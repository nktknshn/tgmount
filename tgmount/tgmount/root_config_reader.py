import logging
import os
from typing import TypeVar, Generator

from tgmount import config, tglog
from tgmount.util import none_fallback
from .root_config_reader_props import RootProducerPropsReader
from .root_config_types import RootConfigContext
from .tgmount_types import TgmountResources
from .types import TgmountRootSource
from .vfs_tree_producer_types import ProducerConfig, VfsStructureConfig

T = TypeVar("T")

logger = tglog.getLogger("TgmountConfigReader")
logger.setLevel(logging.CRITICAL)


class TgmountConfigReader(RootProducerPropsReader):

    DEFAULT_PRODUCER_NAME = "PlainDir"

    def __init__(self) -> None:
        self._logger = logger

    def walk_config_with_ctx(
        self,
        d: TgmountRootSource,
        *,
        resources: TgmountResources,
        ctx: RootConfigContext,
    ) -> Generator[tuple[str, set, VfsStructureConfig, RootConfigContext], None, None]:

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
        producer_cls = None
        # producer_cls = resources.producers.default
        producer_config = None

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

            # if producer_name is not None:
            producer_name = none_fallback(producer_name, self.DEFAULT_PRODUCER_NAME)

            self._logger.info(f"Content will be produced by {producer_name}")

            producer_cls = resources.producers.get_by_name(producer_name)

            # producer_cls = resources.producers.get_producers().get(producer_name)

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
            # vfs_wrappers=vfs_wrappers,
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

    def walk_config(self, d: dict, *, resources: TgmountResources):

        yield from self.walk_config_with_ctx(
            d,
            resources=resources,
            ctx=RootConfigContext(
                current_path=[],
                file_factory=resources.file_factory,
                classifier=resources.classifier,
            ),
        )
