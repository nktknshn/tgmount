from typing import Mapping, TypeVar
from telethon.tl.custom import Message

from tgmount import vfs
from tgmount.tgmount.error import TgmountError
from tgmount.tgclient.messages_collection import MessagesCollection

# from tgmount.tgmount.types import MessagesSet, Set
from tgmount.tgmount.vfs_tree import VfsTreeDir
from tgmount.tgmount.vfs_tree_producer_types import (
    VfsTreeProducerConfig,
    VfsDirConfig,
    VfsTreeProducerProto,
)
from tgmount.util import measure_time
from .logger import logger as _logger

M = TypeVar("M")


class VfsTreeProducerPlainDir(VfsTreeProducerProto):
    logger = _logger.getChild(f"VfsTreeProducerPlainDir")

    def __init__(
        self,
        tree_dir: VfsTreeDir,
        config: VfsTreeProducerConfig,
    ) -> None:
        self._config = config
        self._tree_dir = tree_dir

        # self._messages = MessagesCollection()
        self._message_to_file: dict[int, vfs.FileLike] = {}

        self._logger = self.logger.getChild(f"{self._tree_dir.path}")

    @classmethod
    async def from_config(
        cls,
        resources,
        vfs_config: VfsTreeProducerConfig,
        arg: Mapping,
        tree_dir: VfsTreeDir,
    ):

        return VfsTreeProducerPlainDir(tree_dir, vfs_config)

    # @measure_time(logger_func=print)
    async def produce(self):

        _messages = MessagesCollection.from_iterable(await self._config.get_messages())

        self._logger.info(f"Producing from {len(_messages)} messages...")

        self._message_to_file = {
            m.id: await self._config.produce_file(m) for m in _messages
        }

        if len(self._message_to_file) > 0:
            await self._tree_dir.put_content(
                list(self._message_to_file.values()),
            )

        self._config.message_source.event_new_messages.subscribe(
            self.update_new_messages
        )

        self._config.message_source.event_removed_messages.subscribe(
            self.update_removed_messages
        )

        self._config.message_source.event_edited_messages.subscribe(
            self.update_removed_messages
        )

    async def update_edited_messages(self, source, edited_messages: list[Message]):
        pass

    async def update_new_messages(self, source, new_messages: list[Message]):

        self._logger.info(
            f"update_new_messages({list(map(lambda m: m.id, new_messages))})"
        )

        if len(new_messages) == 0:
            return

        new_messages_set = await self._config.apply_filters(new_messages)

        new_files: list[vfs.FileLike] = [
            await self._config.produce_file(m) for m in new_messages_set
        ]

        self._message_to_file.update(
            {
                **{m.id: f for m, f in zip(new_messages_set, new_files)},
            }
        )

        if len(new_files):
            await self._tree_dir.put_content(new_files)

    async def update_removed_messages(self, source, removed_messages: list[Message]):
        self._logger.info(
            f"update_removed_messages({list(map(lambda m: m.id, removed_messages))})"
        )

        removed_files = [
            self._message_to_file[m.id]
            for m in removed_messages
            if m.id in self._message_to_file
        ]

        for f in removed_files:
            await self._tree_dir.remove_content(f)
