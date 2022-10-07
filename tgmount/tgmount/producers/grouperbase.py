import abc
from typing import Iterable, Mapping, Set, TypeVar

import pathvalidate
from telethon.tl.custom import Message
from tgmount import tglog
from tgmount.tgclient.message_source import MessageSourceSimple, MessagesSet
from tgmount.tgmount.producers.producer_plain import VfsTreePlainDir
from tgmount.tgmount.root_config_types import RootConfigContext
from tgmount.tgmount.tgmount_types import TgmountResources
from tgmount.tgmount.types import Set
from tgmount.tgmount.vfs_tree_producer_types import ProducerConfig
from tgmount.util import sanitize_string_for_path
from tgmount.util.col import sets_difference

from ..vfs_tree import VfsTreeDir
from ..vfs_tree_producer import VfsTreeProducer

TM = TypeVar("TM", bound=Message)

GroupedMessages = tuple[Mapping[str, list[TM]], list[TM]]


class VfsTreeProducerGrouperBase(abc.ABC):
    """
    Base class for a producer that using message_source splits messages into groups creating a directory for each group. The structure of directores is
    defined by `dir_structure`.
    """

    DEFAULT_ROOT_CONFIG: Mapping = {"filter": "All"}
    VfsTreeProducer = VfsTreeProducer
    MessageSource = MessageSourceSimple

    def __init__(
        self,
        tree_dir: VfsTreeDir,
        config: ProducerConfig,
        resources: TgmountResources,
        *,
        dir_structure=DEFAULT_ROOT_CONFIG,
    ) -> None:
        self._dir = tree_dir
        self._config = config
        self._dir_structure = dir_structure
        self._resources = resources

        self._source_by_name: dict[str, VfsTreeProducerGrouperBase.MessageSource] = {}

        self._source_root = self.MessageSource()

        self._logger = tglog.getLogger(f"VfsTreeProducerGrouperBase({self._dir.path})")

    @abc.abstractmethod
    async def group_messages(self, messages: Iterable[Message]) -> GroupedMessages:
        ...

    async def _group_messages(self, messages: Iterable[Message]) -> GroupedMessages:
        group, root = await self.group_messages(messages)
        return {sanitize_string_for_path(k): v for k, v in group.items()}, root

    @property
    def _current_dirs(self) -> Set[str]:
        return frozenset(self._source_by_name.keys())

    async def _add_dir(self, dir_name: str, dir_messages: MessagesSet):
        dir_source = self.MessageSource(messages=dir_messages)
        tree_dir = await self._dir.create_dir(dir_name)

        await self.VfsTreeProducer(self._resources).produce(
            tree_dir,
            self._dir_structure,
            ctx=RootConfigContext.from_resources(
                self._resources, recursive_source=dir_source
            ),
        )

    async def _update_new_message(self, source, messages: Iterable[Message]):
        self._logger.info(f"update_new_messages({list(map(lambda m: m.id, messages))})")

        messages = await self._config.apply_filters(frozenset(messages))
        grouped, root = await self._group_messages(messages)

        removed_dirs, new_dirs, common_dirs = sets_difference(
            self._current_dirs, frozenset(grouped.keys())
        )

        await self._source_root.set_messages(Set(root))

        for d in new_dirs:
            await self._add_dir(d, Set(grouped[d]))

        for d in common_dirs:
            _source = self._source_by_name[d]
            await _source.set_messages(Set(grouped[d]))

    async def _update_removed_messages(self, source, removed_messages: list[Message]):
        self._logger.info(
            f"update_removed_messages({list(map(lambda m: m.id, removed_messages))})"
        )

        grouped, root = await self._group_messages(removed_messages)

        await self._source_root.set_messages(Set(root))

        for dir_name, dir_messages in grouped.items():
            src = self._source_by_name.get(dir_name)

            if src is None:
                self._logger.error(f"Missing source for dir {dir_name}")
                continue

            await src.remove_messages(dir_messages)

            _msgs = await src.get_messages()

            if len(_msgs) == 0:
                await self._dir.remove_subdir(dir_name)
                del self._source_by_name[dir_name]

    async def produce(self):
        messages = await self._config.get_messages()

        grouped, root = await self._group_messages(messages)

        for dir_name, dir_messages in grouped.items():
            await self._add_dir(dir_name, Set(dir_messages))

        await self._source_root.set_messages(Set(root))

        await VfsTreePlainDir(
            self._dir,
            self._config.set_message_source(self._source_root),
        ).produce()

        self._config.message_source.event_new_messages.subscribe(
            self._update_new_message
        )

        self._config.message_source.event_removed_messages.subscribe(
            self._update_removed_messages
        )
