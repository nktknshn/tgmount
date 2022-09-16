import abc
import logging
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
)
from tgmount.util import col, is_not_none, none_fallback

from .filters import Filter, FilterConfigValue

from .tgmount_root_producer_props import RootProducerPropsReader
from .tgmount_root_producer_types import (
    ProducerConfig,
    VfsStructureConfig,
    TgmountRootSource,
    CreateRootContext,
)
from .types import CreateRootResources
from .util import to_list_of_single_key_dicts

T = TypeVar("T")

import tgmount.tglog as log

logger = log.getLogger("TgmountConfigReaderWalker")
logger.setLevel(logging.CRITICAL)


class TgmountConfigReader2:
    def __init__(
        self,
        resources: CreateRootResources,
        logger=logger,
    ) -> None:
        self._logger = logger
        self._resources = resources

    def walk(
        self,
        dir_cfg: TgmountRootSource,
    ):
        yield from self.walk_with_ctx(
            dir_cfg,
            ctx=CreateRootContext(
                current_path=[],
                file_factory=self._resources.file_factory,
                classifier=self._resources.classifier,
            ),
        )

    def walk_with_ctx(self, dir_cfg: TgmountRootSource, ctx: CreateRootContext):
        cfg_reader = TgmountConfigReader()

        yield from cfg_reader.walk_config_with_ctx(
            dir_cfg, resources=self._resources, ctx=ctx
        )


class TgmountConfigReaderWalker:
    def __init__(
        self,
        *,
        dir_cfg: TgmountRootSource,
        resources: CreateRootResources,
        logger=logger,
    ) -> None:
        self._logger = logger
        self._dir = dir_cfg
        self._resources = resources

    def walk(self):
        yield from self.walk_with_ctx(
            ctx=CreateRootContext(
                current_path=[],
                file_factory=self._resources.file_factory,
                classifier=self._resources.classifier,
            ),
        )

    def walk_with_ctx(self, ctx: CreateRootContext):
        cfg_reader = TgmountConfigReader()

        yield from cfg_reader.walk_config_with_ctx(
            self._dir,
            resources=self._resources,
            ctx=ctx,
        )


class TgmountConfigReader(RootProducerPropsReader):
    def __init__(self, logger=logger) -> None:
        self._logger = logger

    def walk_config_with_ctx(
        self,
        d: TgmountRootSource,
        *,
        resources: CreateRootResources,
        ctx: CreateRootContext,
    ):

        current_path_str = (
            f"/{os.path.join(*ctx.current_path)}" if len(ctx.current_path) > 0 else "/"
        )

        logger.info(f"walk_config_with_ctx({current_path_str})")

        other_keys = set(d.keys()).difference(self.PROPS_KEYS)

        source_prop = self.read_prop_source(d)
        filters_prop = self.read_prop_filter(d)
        cache_prop = self.read_prop_cache(d)
        wrappers_prop = self.read_prop_wrappers(d)
        producer_prop = self.read_prop_producer(d)
        treat_as_prop = d.get("treat_as", [])

        if producer_prop:
            self._logger.info(f"producer_prop={producer_prop}")
        if filters_prop:
            self._logger.info(f"filters_prop={filters_prop}")
        if wrappers_prop:
            self._logger.info(f"wrappers_prop={wrappers_prop}")

        message_source = None
        producer_name = None
        producer_arg = None
        producer = None
        producer_cls = resources.producers.default
        producer_config = None

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

            if producer_name is not None:
                self._logger.info(f"Content will be produced by {producer_name}")

                producer_cls = resources.producers.get_producers().get(producer_name)

                if producer_cls is None:
                    raise config.ConfigError(
                        f"Missing producer: {producer_name}. path: {ctx.current_path}"
                    )

        vfs_wrappers = []

        # if wrappers_prop is not None:

        #     for wrapper_name, wrapper_arg in wrappers_prop:
        #         wrapper_cls = resources.vfs_wrappers.get(wrapper_name)

        #         if wrapper_cls is None:
        #             raise config.ConfigError(
        #                 f"Missing wrapper: {wrapper_name}. path: {ctx.current_path}"
        #             )

        #         wrapper = wrapper_cls.from_config(wrapper_arg)
        #         vfs_wrappers.append(wrapper)

        if message_source is not None:
            producer_config = ProducerConfig(
                message_source=message_source,
                factory=current_file_factory,
                filters=filters,
            )

        vfs_config = VfsStructureConfig(
            source_dict=d,
            vfs_producer_name=producer_name,
            vfs_producer=producer_cls,
            vfs_producer_arg=producer_arg,
            vfs_wrappers=vfs_wrappers,
            producer_config=producer_config,
        )

        yield (current_path_str, other_keys, vfs_config, ctx)

        for k in other_keys:
            yield from self.walk_config_with_ctx(
                d[k],
                resources=resources,
                ctx=ctx.add_path(k),
            )

        # return content_from_source

    def walk_config(self, d: dict, *, resources: CreateRootResources):

        yield from self.walk_config_with_ctx(
            d,
            resources=resources,
            ctx=CreateRootContext(
                current_path=[],
                file_factory=resources.file_factory,
                classifier=resources.classifier,
            ),
        )