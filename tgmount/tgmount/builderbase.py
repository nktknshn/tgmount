import abc
from abc import abstractmethod
from collections.abc import Awaitable, Callable, Mapping
from typing import Optional, Type, TypedDict

from dataclasses import dataclass, replace, make_dataclass

from telethon.tl.custom import Message

from tgmount import config, tg_vfs, tgclient, vfs
from tgmount.cache import CacheFactory
from tgmount.cache import source
from tgmount.cache.source import FilesSourceCaching
from tgmount.config import Config, ConfigValidator
from tgmount.config.helpers import dict_get_value
from tgmount.config.types import MessageSource
from tgmount.tg_vfs.file_factory import FileFactory
from tgmount.tgclient import TelegramMessageSource, TgmountTelegramClient
from tgmount.tgclient.message_source import TelegramMessageSourceProto
from tgmount.tgmount.filters import FilterDict
from tgmount.tgmount.producers import TreeProducersProviderProto
from tgmount.util import col, compose_guards, none_fallback

from .tgmountbase import CreateRootResources, Tgmount
from .types import (
    CachesProviderProto,
    Filter,
    FilterProviderProto,
    TgmountRoot,
)

from .wrappers import DirContentWrapperProto, DirWrapperProviderProto


@dataclass
class Context:
    current_path: list[str]
    recursive_source: Optional[TelegramMessageSourceProto] = None
    filters: Optional[list[Filter]] = None

    def set_recursive_source(self, source: Optional[TelegramMessageSourceProto]):
        return replace(self, recursive_source=source)

    def set_filters(self, filters: Optional[list[Filter]]):
        return replace(self, filters=filters)

    def add_path(self, element: str):
        return replace(self, current_path=[*self.current_path, element])


def to_dicts(items: list[str | dict[str, dict]]) -> list[str | dict[str, dict]]:
    res = []

    for item in items:
        if isinstance(item, str):
            res.append(item)
        else:
            res.extend(dict([t]) for t in item.items())

    return res


_filters = TypedDict("_filters", recursive=bool, filters=list[Filter])
# dict_get_value


def _get_filters(
    filt: str | dict[str, dict] | list[str | dict[str, dict]],
    *,
    resources: CreateRootResources,
    ctx: Context,
) -> _filters:
    def _parse_filter(filt: FilterDict) -> list[Filter]:
        return _get_filters(filt, resources=resources, ctx=ctx)["filters"]

    recursive = False

    if isinstance(filt, dict) and "filter" in filt:
        recursive = filt.get("recursive", False)
        if not isinstance(recursive, bool):
            raise config.ConfigError(f"recursive is not bool: {recursive}")

        filt = filt["filter"]

    if not isinstance(filt, list):
        filt = [filt]

    filt = to_dicts(filt)

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
            filter_cons()
            if filter_arg is None
            else filter_cons.from_config(filter_arg, _parse_filter),
        )

    return _filters(recursive=recursive, filters=fs)


async def _process_source(
    d: dict,
    ms: TelegramMessageSourceProto,
    filters: Optional[list[Filter]],
    file_factory: FileFactory,
    content_messages: list[Message],
    *,
    resources: CreateRootResources,
    ctx: Context,
):

    messages = await ms.get_messages()
    messages = [m for m in messages if file_factory.supports(m)]

    if filters is not None:
        for filter_cons in filters:
            messages = await filter_cons.filter(messages)

    for m in messages:
        content_messages.append(m)


async def _tgmount_root(
    d: dict, *, resources: CreateRootResources, ctx=Context(current_path=[])
) -> vfs.DirContentProto:
    _source = d.get("source")
    _filter = d.get("filter")
    cache = d.get("cache")
    wrappers = d.get("wrappers")
    _producer_dict = d.get("producer")

    other_keys = set(d.keys()).difference(
        {"source", "filter", "cache", "wrappers", "producer"},
    )

    file_factory = (
        resources.file_factory if cache is None else resources.caches.get(cache)
    )

    if file_factory is None:
        raise config.ConfigError(f"missing cache named {cache} in {ctx.current_path}")

    content_messages: tg_vfs.MessagesTree = []

    filters = none_fallback(ctx.filters, [])
    recursive_filter = False

    if _filter is not None:
        _filters = _get_filters(
            filt=_filter,
            resources=resources,
            ctx=ctx,
        )

        filters = [*filters, *_filters["filters"]]

        if _filters["recursive"] is True:
            recursive_filter = True
            ctx = ctx.set_filters(filters)

    if _source is not None:
        if isinstance(_source, str):
            source_name = _source
            recursive = False
        else:
            source_name = _source["source"]
            recursive = _source.get("recursive", False)

        ms = resources.sources.get(source_name)

        if ms is None:
            raise config.ConfigError(
                f"missing message source {_source} in {ctx.current_path}"
            )

        if not recursive:
            await _process_source(
                d,
                ms,
                filters,
                file_factory,
                content_messages,
                resources=resources,
                ctx=ctx,
            )

        if recursive:
            ctx = ctx.set_recursive_source(ms)

    elif (
        ctx.recursive_source is not None
        and _filter is not None
        and not recursive_filter
    ):
        await _process_source(
            d,
            ctx.recursive_source,
            filters,
            file_factory,
            content_messages,
            resources=resources,
            ctx=ctx,
        )
    elif len(other_keys) == 0:
        raise config.ConfigError(
            f"missing source, subfolders or filter in {ctx.current_path}"
        )

    if _producer_dict is not None:
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
        file_factory.create_dir_content_source(content_messages),
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

        wrappers = to_dicts(wrappers)

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


class TgmountBuilderBase(abc.ABC):
    TelegramClient: Type[tgclient.TgmountTelegramClient]
    MessageSource: Type[tgclient.TelegramMessageSource]
    FilesSource: Type[tgclient.TelegramFilesSource]
    FileFactory: Type[tg_vfs.FileFactory]

    caches: CachesProviderProto
    filters: FilterProviderProto
    wrappers: DirWrapperProviderProto
    producers: TreeProducersProviderProto

    async def create_tgmount(self, cfg: Config) -> Tgmount:
        client = await self.create_client(cfg)
        messssage_sources = {
            k: await self.create_message_source(client, ms)
            for k, ms in cfg.message_sources.sources.items()
        }

        if cfg.caches is not None:
            caches = {
                k: await self.create_cached_file_source(client, cache_config)
                for k, cache_config in cfg.caches.caches.items()
            }
        else:
            caches = {}

        # if cfg.wrappers is not None:
        #     wrappers = {
        #         k: await self.create_wrapper(wrapper_config)
        #         for k, wrapper_config in cfg.wrappers.wrappers.items()
        #     }
        # else:
        #     wrappers = {}

        files_source = self.FilesSource(client)
        file_factory = self.FileFactory(files_source)

        tgm = Tgmount(
            client=client,
            file_factory=file_factory,
            filters=self.filters.get_filters(),
            producers=self.producers.get_producers(),
            message_sources=messssage_sources,
            mount_dir=cfg.mount_dir,
            wrappers=self.wrappers.get_wrappers(),
            caches=caches,
            root=self.parse_root_dict(cfg.root.content),
        )

        for k, v in messssage_sources.items():
            v.subscribe(tgm.update)

        return tgm

    async def create_cached_file_source(
        self, client: TgmountTelegramClient, cache_config: config.Cache
    ) -> tg_vfs.FileFactory:
        cache_factory_cls = await self.caches.get_cache_factory(cache_config.type)

        cache = cache_factory_cls(**cache_config.kwargs)

        fsc = FilesSourceCaching(client, cache)

        return self.FileFactory(fsc)

    # async def create_wrapper(self, w: config.Wrapper) -> DirWrapper:
    #     cons = await self.wrappers.get_wrappers_factory(w.type)

    #     return await cons(**w.kwargs)

    async def create_client(self, cfg: Config):
        return self.TelegramClient(
            cfg.client.session,
            cfg.client.api_id,
            cfg.client.api_hash,
        )

    async def create_message_source(
        self,
        client: tgclient.TgmountTelegramClient,
        ms: config.MessageSource,
    ) -> tgclient.TelegramMessageSource:
        return self.MessageSource(client, ms.entity, ms.limit)

    def parse_root_dict(self, d: dict) -> TgmountRoot:
        return lambda ctx: _tgmount_root(
            d,
            resources=ctx,
        )
