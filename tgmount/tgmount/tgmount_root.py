import abc
from abc import abstractmethod
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, make_dataclass, replace
from typing import Optional, Type, TypeVar, TypedDict

from telethon.tl.custom import Message

from tgmount import config, tg_vfs, tgclient, vfs
from tgmount.tg_vfs import FileFactoryProto
from tgmount.tg_vfs.tree.message_tree import create_dir_content_source
from tgmount.tgclient.message_source import TelegramMessageSourceProto
from tgmount.tgmount.filters import FilterConfigValue
from tgmount.util import col, is_not_none, none_fallback

from .filters import Filter
from .tgmountbase import CreateRootResources
from .util import to_list_of_single_key_dicts

T = TypeVar("T")


@dataclass
class CreateRootContext:
    current_path: list[str]
    file_factory: FileFactoryProto
    classifier: tg_vfs.ClassifierBase
    recursive_source: Optional[TelegramMessageSourceProto] = None
    recursive_filters: Optional[list[Filter]] = None

    def set_recursive_source(self, source: Optional[TelegramMessageSourceProto]):
        return replace(self, recursive_source=source)

    def set_recursive_filters(self, recursive_filters: Optional[list[Filter]]):
        return replace(self, recursive_filters=recursive_filters)

    def extend_recursive_filters(self, filters: list[Filter]):
        return replace(
            self,
            recursive_filters=[*none_fallback(self.recursive_filters, []), *filters],
        )

    def set_file_factory(self, file_factory: FileFactoryProto):
        return replace(self, file_factory=file_factory)

    def add_path(self, element: str):
        return replace(self, current_path=[*self.current_path, element])


async def tgmount_root(
    d: dict, *, resources: CreateRootResources
) -> vfs.DirContentProto:
    return await _tgmount_root(
        d,
        resources=resources,
        ctx=CreateRootContext(
            current_path=[],
            file_factory=resources.file_factory,
            classifier=resources.classifier,
        ),
    )


_filters = TypedDict("_filters", recursive=bool, filters=list[Filter])

# def validate_filter_config_value(value: FilterConfigValue):
#     pass


def get_filters(
    filt: FilterConfigValue,
    *,
    resources: CreateRootResources,
    ctx: CreateRootContext,
) -> _filters:
    def _parse_filter(filt: FilterConfigValue) -> list[Filter]:
        return get_filters(filt, resources=resources, ctx=ctx)["filters"]

    filter_recursive = False

    if isinstance(filt, dict) and "filter" in filt:
        filter_recursive = filt.get("recursive", False)
        if not isinstance(filter_recursive, bool):
            raise config.ConfigError(f"recursive is not bool: {filter_recursive}")

        filt = filt["filter"]

    if not isinstance(filt, list):
        filt = [filt]

    filt = to_list_of_single_key_dicts(filt)

    fs: list[Filter] = []

    for f_item in filt:
        if isinstance(f_item, str):
            filter_cons = resources.filters.get(f_item)
            filter_arg = None
        else:
            f_name, filter_arg = col.get_first_pair(f_item)
            filter_cons = resources.filters.get(f_name)

        if filter_cons is None:
            raise config.ConfigError(f"missing filter: {f_item} in {ctx.current_path}")

        fs.append(
            filter_cons.from_config(filter_arg, ctx, _parse_filter),
        )

    return _filters(recursive=filter_recursive, filters=fs)


async def get_source_messages(
    ms: TelegramMessageSourceProto,
    filters: Optional[list[Filter]],
    file_factory: FileFactoryProto,
    treat_as: list[str],
):
    source_messages = []
    messages = await ms.get_messages()
    # messages = [m for m in messages if file_factory.supports(m)]
    messages = list(
        filter(is_not_none, [file_factory.try_get(m, treat_as) for m in messages])
    )

    if filters is not None:
        for filter_cons in filters:
            messages = await filter_cons.filter(messages)

    for m in messages:
        source_messages.append(m)

    return source_messages


async def _tgmount_root(
    d: dict,
    *,
    resources: CreateRootResources,
    ctx: CreateRootContext,
) -> vfs.DirContentProto:
    _source = d.get("source")
    _filter = d.get("filter")
    cache = d.get("cache")
    wrappers = d.get("wrappers")
    _producer_dict = d.get("producer")
    _treat_as = d.get("treat_as", [])

    if not isinstance(_treat_as, list):
        _treat_as = [_treat_as]

    other_keys = set(d.keys()).difference(
        {"source", "filter", "cache", "wrappers", "producer", "treat_as"},
    )

    file_factory = ctx.file_factory if cache is None else resources.caches.get(cache)

    if file_factory is None:
        raise config.ConfigError(f"missing cache named {cache} in {ctx.current_path}")

    content_messages: tg_vfs.MessagesTree = []

    filters = none_fallback(ctx.recursive_filters, [])
    recursive_filter = False

    if _filter is not None:
        _filters = get_filters(
            filt=_filter,
            resources=resources,
            ctx=ctx,
        )

        filters.extend(_filters["filters"])

        if _filters["recursive"] is True:
            recursive_filter = True
            # ctx = ctx.set_recursive_filters(filters)

    if _source is not None:
        if isinstance(_source, str):
            source_name = _source
            recursive = False
        else:
            source_name = _source["source"]
            recursive = _source.get("recursive", False)

        message_source = resources.sources.get(source_name)

        if message_source is None:
            raise config.ConfigError(
                f"missing message source {_source} in {ctx.current_path}"
            )

        if not recursive:
            _messages = await get_source_messages(
                message_source, filters, file_factory, _treat_as
            )

            content_messages.extend(_messages)

        if recursive:
            ctx = ctx.set_recursive_source(message_source)

    elif (
        ctx.recursive_source is not None
        and _filter is not None
        and not recursive_filter
    ):
        _messages = await get_source_messages(
            ctx.recursive_source, filters, file_factory, _treat_as
        )
        content_messages.extend(_messages)

    elif len(other_keys) == 0:
        raise config.ConfigError(
            f"missing source, subfolders or filter in {ctx.current_path}"
        )

    if _producer_dict is not None:
        if isinstance(_producer_dict, str):
            _producer_dict = {_producer_dict: {}}

        producer_name = col.get_first_key(_producer_dict)

        if producer_name is None:
            raise config.ConfigError(
                f"Invalid producer definition: {_producer_dict} in {ctx.current_path}"
            )

        producer_cls = resources.producers.get(producer_name)

        if producer_cls is None:
            raise config.ConfigError(
                f"Missing producer: {producer_name}. path: {ctx.current_path}"
            )

        def _parse_root_func(d: dict):
            async def _inner(ms: list[Message]):
                return await _tgmount_root(
                    d,
                    resources=resources,
                    ctx=ctx.set_recursive_source(
                        TelegramMessageSourceProto.from_messages(ms)
                    ).add_path(producer_name),
                )

            return _inner

        producer = producer_cls.from_config(
            _producer_dict[producer_name],
            _parse_root_func,
        )

        content_messages = await producer.produce_tree(content_messages)

    content = vfs.dir_content_from_source(
        create_dir_content_source(file_factory, content_messages, _treat_as),
    )

    other_keys_content = []
    for k in other_keys:
        _content = await _tgmount_root(
            d[k],
            resources=resources,
            ctx=ctx.add_path(k),
        )
        other_keys_content.append(vfs.vdir(k, _content))

    content = vfs.dir_content_extend(
        content,
        vfs.dir_content(*other_keys_content),
    )

    if wrappers is not None:
        if not isinstance(wrappers, list):
            wrappers = [wrappers]

        wrappers = to_list_of_single_key_dicts(wrappers)

        for w_item in wrappers:
            if isinstance(w_item, str):
                wrapper_name = w_item
                wrapper_arg = None
            else:
                wrapper_name, wrapper_arg = col.get_first_pair(w_item)

            wrapper_cons = resources.wrappers.get(wrapper_name)

            if wrapper_cons is None:
                raise config.ConfigError(
                    f"missing wrapper: {wrapper_name} in {ctx.current_path}"
                )
            if wrapper_arg is None:
                wrapper = wrapper_cons()
            else:
                wrapper = wrapper_cons.from_config(wrapper_arg)

            content = await wrapper.wrap_dir_content(content)

    return content
