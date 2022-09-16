import abc
import os
from abc import abstractmethod
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field, make_dataclass, replace
from typing import Any, Optional, Protocol, Type, TypedDict, TypeVar

from telethon.tl.custom import Message

from tgmount import config, tg_vfs, tgclient, vfs
from tgmount.tg_vfs import FileFactoryProto
from tgmount.tg_vfs.tree.message_tree import create_dir_content_source
from tgmount.tgclient import message_source
from tgmount.tgclient.guards import MessageDownloadable
from tgmount.tgclient.message_source import MessageSourceProto
from tgmount.tgmount.filters import FilterConfigValue
from tgmount.tgmount.tgmount_root_producer_props import RootProducerPropsReader
from tgmount.util import col, is_not_none, none_fallback

from .filters import Filter
from .logger import logger
from .tgmountbase import CreateRootResources
from .util import to_list_of_single_key_dicts
from .tgmount_root_producer_types import *

T = TypeVar("T")


def message_to_tuple(m: Message) -> MessageTuple:
    return (m.id, MessageDownloadable.document_or_photo_id(m))


class ProducedContent:
    def __init__(self, mapping: ProducedContentMapping) -> None:
        self._mapping: ProducedContentMapping = mapping

    @staticmethod
    def init_from_sources(sources: Mapping[str, tgclient.MessageSourceProto]):
        result = {}

        for src_name, src in sources.items():
            result[src] = {}

        return ProducedContent(result)

    def add_content(self, path: str, content: ProducedDirContent):
        self._mapping[content.message_source][path] = content


class TgmountRootProducer(RootProducerPropsReader):
    def __init__(self, logger=logger) -> None:
        self._logger = logger
        self._produced_content = None

    def get_filters_from_prop(
        self, filter_prop: list, resources: CreateRootResources, ctx: CreateRootContext
    ) -> list[Filter]:
        def _parse_filter(filt: FilterConfigValue) -> list[Filter]:
            filter_prop = self.read_prop_filter({"filter": filt})
            if filter_prop is None:
                return []
            return self.get_filters_from_prop(filter_prop["filters"], resources, ctx)

        filters = []
        for f_name, f_arg in filter_prop:
            filter_cls = resources.filters.get(f_name)

            if filter_cls is None:
                raise config.ConfigError(
                    f"missing filter: {f_name} in {ctx.current_path}"
                )

            _filter = filter_cls.from_config(f_arg, ctx, _parse_filter)

            filters.append(_filter)

        return filters

    async def get_root(self, d: dict, *, resources: CreateRootResources):

        produced_content = ProducedContent.init_from_sources(resources.sources)

        result = await self._get_root(
            d,
            resources=resources,
            ctx=CreateRootContext(
                current_path=[],
                file_factory=resources.file_factory,
                classifier=resources.classifier,
            ),
            produced_content=produced_content,
        )

        self._produced_content = produced_content
        return result

    async def _get_root(
        self,
        d: TgmountRootSource,
        *,
        resources: CreateRootResources,
        ctx: CreateRootContext,
        produced_content: ProducedContent,
    ) -> vfs.DirContentProto:

        current_path_str = (
            os.path.join(*ctx.current_path) if len(ctx.current_path) > 0 else "/"
        )
        logger.info(f"get_root({current_path_str})")

        other_keys = set(d.keys()).difference(self.PROPS_KEYS)

        source_prop = self.read_prop_source(d)
        filters_prop = self.read_prop_filter(d)
        cache_prop = self.read_prop_cache(d)
        wrappers_prop = self.read_prop_wrappers(d)
        producer_prop = self.read_prop_producer(d)
        treat_as_prop = d.get("treat_as", [])

        message_source = None
        producer_name = None
        producer_arg = None
        producer = None

        input_messages = []
        filtered_source_messages = []
        produced_tree = None
        content_from_source = None

        if cache_prop is not None:
            self._logger.info(f"Cache {cache_prop} will be used for files contents")

        current_file_factory = (
            ctx.file_factory if cache_prop is None else resources.caches.get(cache_prop)
        )

        if current_file_factory is None:
            raise config.ConfigError(
                f"missing cache named {cache_prop} in {ctx.current_path}"
            )

        filters_from_prop = (
            self.get_filters_from_prop(filters_prop["filters"], resources, ctx)
            if filters_prop is not None
            else None
        )

        filters_from_ctx = none_fallback(ctx.recursive_filters, [])

        filters = [*filters_from_ctx, *none_fallback(filters_from_prop, [])]

        """
        the dir will produce content from messages source and apllying filter in cases when:
        1. source_prop is specified and it's not recursive
        2. recursive_source is in the context and a filters_prop specified and it's not recursive
        3. source_prop or recursive_source is specified and producer_prop is specified
        """
        if source_prop is not None and not source_prop["recursive"]:

            self._logger.info(f"1. source_prop is specified and it's not recursive")

            message_source = resources.sources.get(source_prop["source_name"])

            if message_source is None:
                raise config.ConfigError(
                    f"Missing message source {source_prop['source_name']} used at {ctx.current_path}"
                )

        elif (
            ctx.recursive_source is not None
            and filters_prop is not None
            and not filters_prop["recursive"]
        ):
            self._logger.info(
                f"2. recursive_source is in the context and a filters_prop specified: {filters_prop}"
            )
            message_source = ctx.recursive_source
        elif (
            source_prop is not None or ctx.recursive_source is not None
        ) and producer_prop is not None:
            self._logger.info(
                f"3. source_prop or recursive_source is specified and producer_prop is specified: {producer_prop}"
            )

            if source_prop is not None:
                message_source = resources.sources.get(source_prop["source_name"])
            else:
                message_source = ctx.recursive_source

            if source_prop is not None and message_source is None:
                raise config.ConfigError(
                    f"Missing message source {source_prop['source_name']} used at {ctx.current_path}"
                )

            producer_name, producer_arg = producer_prop

        elif source_prop is not None and source_prop["recursive"]:
            # if source_prop is recursive update context
            self._logger.info(
                f"Setting recoursive message source: {source_prop['source_name']}"
            )
            recursive_message_source = resources.sources.get(source_prop["source_name"])

            if recursive_message_source is None:
                raise config.ConfigError(
                    f"Missing message source {source_prop['source_name']} used at {ctx.current_path}"
                )
            ctx = ctx.set_recursive_source(recursive_message_source)
        elif len(other_keys) == 0:
            raise config.ConfigError(
                f"Missing source, subfolders or filter in {ctx.current_path}"
            )

        if filters_prop is not None and filters_prop["recursive"] and filters_from_prop:
            self._logger.info(
                f"Setting recoursive message filters: {filters_prop['filters']}"
            )
            ctx = ctx.extend_recursive_filters(filters_from_prop)

        if message_source is not None:
            self._logger.info(f"The folder will be containing files")

            input_messages = (
                filtered_source_messages
            ) = await message_source.get_messages()

            # filter out unsupported types
            filtered_source_messages = list(
                filter(
                    is_not_none,
                    [
                        current_file_factory.try_get(m, treat_as_prop)
                        for m in filtered_source_messages
                    ],
                )
            )

            # filter with filters
            for f in filters:
                filtered_source_messages = await f.filter(filtered_source_messages)

            if producer_name is not None:

                def _parse_root_func(d: dict):
                    async def _inner(ms: list[Message]):
                        return await self._get_root(
                            d,
                            resources=resources,
                            ctx=ctx.set_recursive_source(
                                MessageSourceProto.from_messages(ms)
                            ).add_path(producer_name),
                            produced_content=produced_content,
                        )

                    return _inner

                producer_cls = resources.producers.get(producer_name)

                if producer_cls is None:
                    raise config.ConfigError(
                        f"Missing producer: {producer_name}. path: {ctx.current_path}"
                    )

                producer = producer_cls.from_config(producer_arg, _parse_root_func)
                produced_tree = await producer.produce_tree(filtered_source_messages)

            if produced_tree is not None:
                content_from_source = vfs.dir_content_from_source(
                    create_dir_content_source(
                        current_file_factory, produced_tree, treat_as_prop
                    ),
                )
            else:
                content_from_source = vfs.dir_content_from_source(
                    create_dir_content_source(
                        current_file_factory, filtered_source_messages, treat_as_prop
                    ),
                )

        other_keys_content = []

        for k in other_keys:
            _content = await self._get_root(
                d[k],
                resources=resources,
                ctx=ctx.add_path(k),
                produced_content=produced_content,
            )
            other_keys_content.append(vfs.vdir(k, _content))

        if content_from_source:
            dir_content = vfs.dir_content_extend(
                content_from_source,
                vfs.dir_content(*other_keys_content),
            )
        else:
            dir_content = vfs.dir_content(*other_keys_content)

        if message_source:
            produced_content.add_content(
                current_path_str,
                ProducedDirContent(
                    message_source=message_source,
                    factory=current_file_factory,
                    filtered_source_messages_set=list(
                        map(message_to_tuple, filtered_source_messages)
                    ),
                    input_source_messages=list(map(message_to_tuple, input_messages)),
                    filters=filters,
                    result_content=dir_content,
                    producer=producer,
                ),
            )

        return dir_content
