import abc
import os
import traceback
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
from tgmount.tgclient.message_source import (
    MessageSourceProto,
    MessageSourceProto,
)
from tgmount.util import col, is_not_none, none_fallback

from .filters import Filter, FilterConfigValue
from .logger import logger
from .producers import (
    TreeProducer,
    TreeProducerFilter,
    TreeProducerNoop,
    async_id,
    noop_producer,
)
from .tgmount_root_producer_props import RootProducerPropsReader
from .tgmount_root_producer_types import *
from .types import CreateRootResources
from .util import to_list_of_single_key_dicts

T = TypeVar("T")


class ProducedContentDirContent(vfs.DirContentProto):
    """DirContent wrapper"""

    def __init__(self, produce_content: "ProducedContent", path: str) -> None:
        self._produce_content = produce_content
        self._path = path

    async def readdir_func(self, handle, off: int):
        logger.info(f"ProducedContentDirContent({self._path}).readdir_func({off})")
        return await self._produce_content._get_by_path(self._path).readdir_func(
            handle, off
        )

    async def opendir_func(self):
        logger.info(f"ProducedContentDirContent({self._path}).opendir_func()")
        return await self._produce_content._get_by_path(self._path).opendir_func()

    async def releasedir_func(self, handle):
        logger.info(f"ProducedContentDirContent({self._path}).releasedir_func()")
        return await self._produce_content._get_by_path(self._path).releasedir_func(
            handle
        )


class ProducedContent:
    """
    Updatable structure of vfs entities produced from root config
    Returned vfs entities should only depend on this structure
    So when updated here it is automatically updated in FilesystemOperations
    """

    def __init__(
        self, mapping: ProducedContentMapping, file_factory: FileFactoryProto
    ) -> None:
        self._mapping_by_source: ProducedContentMapping = mapping

        self._mapping_by_path_producer: dict[str, ProducerConfig] = {}
        self._mapping_by_path_content: dict[str, vfs.DirContentProto] = {}
        self._mapping_by_path_other_keys: dict[str, set[str]] = {}

        self._file_factory: FileFactoryProto = file_factory

        self._logger = logger

    def add_messages_source(self, message_source: MessageSourceProto):
        self._mapping_by_source[message_source] = {}

    def get_vfs_root(self) -> vfs.VfsRoot:
        return vfs.root(self.get_by_path("/"))

    def get_by_path(self, path: str) -> vfs.DirContentProto:
        return ProducedContentDirContent(self, path)

    def _get_by_path(self, path: str) -> vfs.DirContentProto:
        self._logger.info(f"get_by_path({path})")
        # self._logger.info(traceback.format_exc())

        dir_content = self._mapping_by_path_content.get(path)
        other_keys = self._mapping_by_path_other_keys.get(path, [])

        result = {}

        for key in other_keys:
            item_path = os.path.join(path, key)
            result[key] = ProducedContentDirContent(
                produce_content=self, path=item_path
            )

        if dir_content is not None:
            return vfs.dir_content_extend(
                dir_content, vfs.dir_content_from_source(result)
            )

        return vfs.dir_content_from_source(result)

    def add_other_key(self, path: str, key: str):
        self._logger.info(f"parent_path={path}, key={key}")

        if path not in self._mapping_by_path_other_keys:
            self._mapping_by_path_other_keys[path] = set()

        self._mapping_by_path_other_keys[path].add(key)

        if path != "/" and path != "":
            basename = os.path.basename(path)
            parent_path = os.path.dirname(path)

            self.add_other_key(parent_path, basename)

    def add_produced_content(self, path: str, content: ProducedDirContent):
        self._logger.info(f"add_produced_content({path})")

        self._mapping_by_source[content.producer_config.message_source][path] = content
        self._mapping_by_path_content[path] = content.result_content
        self._mapping_by_path_producer[path] = content.producer_config

        if path != "/" and path != "":
            basename = os.path.basename(path)
            parent_path = os.path.dirname(path)

            self.add_other_key(parent_path, basename)

    async def on_update(self, source: tgclient.MessageSourceProto):
        messages = await source.get_messages()

        source_content = self._mapping_by_source.get(source)

        if source_content is None:
            self._logger.error(
                f"Source {source} was not found in {set(self._mapping_by_source.keys())}"
            )
            return

        needs_update: list[tuple[str, ProducedDirContent]] = []

        supported_source_messages = self._file_factory.filter_supported(messages)
        supported_source_messages_set = messages_to_tuples_set(
            supported_source_messages
        )

        for path, content in source_content.items():
            self._logger.info(f"checking {path}")
            if len(content.supported_source_messages_set) != len(
                supported_source_messages_set
            ):
                self._logger.info(f"needs update")
                needs_update.append((path, content))
            elif content.supported_source_messages_set != supported_source_messages_set:
                self._logger.info(f"needs update")
                needs_update.append((path, content))
            else:
                self._logger.info(f"doesnt need update")
                continue

        for path, content in needs_update:
            self._logger.info(f"checking {path} from needs_update")
            filtered_messages = await content.dir_producer.apply_filters(
                supported_source_messages
            )

            filtered_messages_set = messages_to_tuples_set(filtered_messages)

            if filtered_messages_set == content.filtered_source_messages_set:
                self._logger.info(f"filtered messages are same")
                continue

            self._logger.info(f"updating")

            new_content = await content.dir_producer.produce_content_from_filtered(
                filtered_messages
            )

            content.result_content = new_content
            content.filtered_source_messages_set = filtered_messages_set
            content.supported_source_messages_set = supported_source_messages_set

            self._mapping_by_path_content[path] = new_content

    @staticmethod
    def init_from_resources(resources: CreateRootResources):
        result = {}

        for src_name, src in resources.sources.items():
            result[src] = {}

        return ProducedContent(
            result,
            file_factory=resources.file_factory,
        )


class TgmountRootProducer(RootProducerPropsReader):
    def __init__(self, logger=logger) -> None:
        self._logger = logger
        self._produced_content = None

    async def read_config(
        self,
        d: TgmountRootSource,
        *,
        resources: CreateRootResources,
        ctx: CreateRootContext,
    ):
        pass

    async def _build_root(
        self,
        d: TgmountRootSource,
        *,
        resources: CreateRootResources,
        ctx: CreateRootContext,
        produced_content: ProducedContent,
    ):

        current_path_str = (
            f"/{os.path.join(*ctx.current_path)}" if len(ctx.current_path) > 0 else "/"
        )

        logger.info(f"get_root({current_path_str})")

        other_keys = set(d.keys()).difference(self.PROPS_KEYS)

        source_prop = self.read_prop_source(d)
        filters_prop = self.read_prop_filter(d)
        cache_prop = self.read_prop_cache(d)
        wrappers_prop = self.read_prop_wrappers(d)
        producer_prop = self.read_prop_producer(d)
        treat_as_prop = d.get("treat_as", [])

        self._logger.info(f"producer_prop={producer_prop}")

        message_source = None
        producer_name = None
        producer_arg = None
        producer = None

        supported_source_messages = []
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
            and producer_prop is None
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
            filtered_source_messages = (
                supported_source_messages
            ) = current_file_factory.filter_supported(
                filtered_source_messages, treat_as=treat_as_prop
            )

            # filter with filters
            for f in filters:
                filtered_source_messages = await f.filter(filtered_source_messages)

            if producer_name is not None:
                self._logger.info(f"Content will be produced by {producer_name}")

                def _parse_root_func(d: dict):
                    async def _inner(ms: list[Message]):
                        return await self._build_root(
                            d,
                            resources=resources,
                            ctx=ctx.set_recursive_source(
                                message_source
                                # TelegramMessageSourceProto.from_messages(ms)
                            )
                            # .add_path(producer_name)
                            ,
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

        for k in other_keys:
            await self._build_root(
                d[k],
                resources=resources,
                ctx=ctx.add_path(k),
                produced_content=produced_content,
            )

        if message_source is not None and content_from_source is not None:

            _produced_content = ProducedDirContent(
                producer_config=ProducerConfig(
                    message_source=message_source,
                    factory=current_file_factory,
                    filters=filters,
                    vfs_producer=producer,
                ),
                filtered_source_messages_set=messages_to_tuples(
                    filtered_source_messages
                ),
                # input_source_messages=set(messages_to_tuples(input_messages)),
                supported_source_messages_set=messages_to_tuples(
                    supported_source_messages
                ),
                result_content=content_from_source,
            )

            produced_content.add_produced_content(current_path_str, _produced_content)

        # return content_from_source

    async def build_root(self, d: dict, *, resources: CreateRootResources):

        produced_content = ProducedContent.init_from_resources(resources)

        result = await self._build_root(
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
