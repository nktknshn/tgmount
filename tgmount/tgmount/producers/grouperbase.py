import abc
import os
from typing import Iterable, Mapping, TypeVar

from tgmount.tgclient.message_source import MessageSource
from tgmount.tgclient.message_types import MessageProto

from ..error import TgmountError
from ..producers.producer_plain import VfsTreeProducerPlainDir
from ..root_config_types import RootConfigWalkingContext
from ..tgmount_types import TgmountResources
from ..vfs_tree_producer_types import VfsTreeProducerConfig

from tgmount.util import sanitize_string_for_path
from tgmount.util.col import sets_difference
from tgmount.util.func import map_values
from tgmount.util.timer import Timer

from ..vfs_tree import VfsTreeDir
from ..vfs_tree_producer import VfsTreeProducer
from .logger import logger as _logger

M = TypeVar("M", bound=MessageProto)
GroupedMessages = tuple[Mapping[str, list[M]], list[M]]


class VfsTreeProducerGrouperBase(abc.ABC):
    """
    Base class for a producer that splits messages into groups creating a directory for each group. The structure of directores is
    defined by `dir_structure`.
    """

    logger = _logger.getChild("VfsTreeProducerGrouperBase")

    DEFAULT_ROOT_CONFIG: Mapping = {"filter": "All"}
    VfsTreeProducer = VfsTreeProducer
    MessageSource = MessageSource[MessageProto]

    def __init__(
        self,
        tree_dir: VfsTreeDir,
        config: VfsTreeProducerConfig,
        resources: TgmountResources,
        *,
        dir_structure=DEFAULT_ROOT_CONFIG,
    ) -> None:
        self._dir = tree_dir
        self._config = config
        self._dir_structure = dir_structure
        self._resources = resources

        self._source_by_name: dict[str, VfsTreeProducerGrouperBase.MessageSource] = {}

        self._source_root = self.MessageSource(tag=os.path.join(self._dir.path))

        self._logger = self.logger.getChild(f"{self._dir.path}")

    @classmethod
    def sanitize(cls, dirname: str):
        return sanitize_string_for_path(dirname)

    @abc.abstractmethod
    async def group_messages(self, messages: Iterable[M]) -> GroupedMessages[M]:
        ...

    async def _group_messages(self, messages: Iterable[M]) -> GroupedMessages[M]:
        group, root = await self.group_messages(messages)
        return {self.sanitize(k): v for k, v in group.items()}, root

    @property
    def _current_dirs(self) -> frozenset[str]:
        return frozenset(self._source_by_name.keys())

    async def _add_dir(self, dir_name: str, dir_messages: list[MessageProto]):

        dir_source = self.MessageSource(
            messages=dir_messages, tag=f"{os.path.join(self._dir.path, dir_name)}"
        )

        tree_dir = await self._dir.create_dir(dir_name)
        # tree_dir.additional_data = self._dir.additional_data

        self._source_by_name[dir_name] = dir_source

        await self.VfsTreeProducer(self._resources).produce(
            tree_dir,
            self._dir_structure,
            ctx=RootConfigWalkingContext.from_resources(
                self._resources, recursive_source=dir_source
            ),
        )

    async def _update_new_message(self, source, messages: Iterable[MessageProto]):
        self._logger.info(f"update_new_messages({list(map(lambda m: m.id, messages))})")

        messages = await self._config.apply_filters(messages)

        self._logger.debug(f"after filtering left {len(messages)} messages")

        grouped, root = await self._group_messages(messages)

        removed_dirs, new_dirs, common_dirs = sets_difference(
            self._current_dirs, frozenset(grouped.keys())
        )

        self._logger.debug(f"new_dirs={new_dirs} common_dirs={common_dirs}")

        await self._source_root.set_messages(root)

        for d in new_dirs:
            await self._add_dir(d, grouped[d])

        for d in common_dirs:
            self._logger.debug(f"updating {d}")
            _source = self._source_by_name.get(d)

            if _source is None:
                raise TgmountError(f"Missing source for dir {d}")

            await _source.add_messages(grouped[d])

    async def _update_edited_messages(
        self,
        source,
        old_messages: list[MessageProto],
        removed_messages: list[MessageProto],
    ):
        self._logger.info(
            f"_update_edited_messages({list(map(lambda m: m.id, old_messages))})"
        )

    async def _update_removed_messages(
        self, source, removed_messages: list[MessageProto]
    ):
        self._logger.info(
            f"update_removed_messages({list(map(lambda m: m.id, removed_messages))})"
        )

        grouped, root = await self._group_messages(removed_messages)

        await self._source_root.set_messages(root)

        for dir_name, dir_messages in grouped.items():
            dir_src = self._source_by_name.get(dir_name)

            if dir_src is None:
                self._logger.error(f"Missing source for dir {dir_name}")
                continue

            await dir_src.remove_messages(dir_messages)

            _msgs = await dir_src.get_messages()

            if len(_msgs) == 0:
                await self._dir.remove_subdir(dir_name)
                del self._source_by_name[dir_name]

    async def produce(self):
        t1 = Timer()

        t1.start("messages")
        messages = await self._config.get_messages()

        t1.start("grouping")
        grouped, root = await self._group_messages(messages)

        t1.start("subdirs")
        for dir_name, dir_messages in grouped.items():
            await self._add_dir(dir_name, dir_messages)

        t1.start("root")

        await self._source_root.set_messages(root)

        await VfsTreeProducerPlainDir(
            self._dir,
            self._config.set_message_source(self._source_root),
        ).produce()

        t1.stop()

        self._config.message_source.event_new_messages.subscribe(
            self._update_new_message
        )

        self._config.message_source.event_removed_messages.subscribe(
            self._update_removed_messages
        )

        self._config.message_source.event_edited_messages.subscribe(
            self._update_edited_messages
        )

        self._logger.debug(f"Producing took: {t1.total:.2f} ms.")
        self._logger.debug(f"{map_values(lambda v: f'{v:.2f}', t1.durations)}")
