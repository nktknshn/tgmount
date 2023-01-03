from telethon.tl.custom import Message

from tgmount import vfs, tglog
from tgmount.tgmount.error import TgmountError
from tgmount.tgmount.types import MessagesSet, Set
from tgmount.tgmount.vfs_tree import VfsTreeDir
from tgmount.tgmount.vfs_tree_producer_types import (
    ProducerConfig,
    VfsStructureConfig,
    VfsTreeProducerProto,
)
from tgmount.util import measure_time


class VfsTreePlainDir(VfsTreeProducerProto):
    logger = tglog.getLogger(f"VfsTreePlainDir")

    def __init__(self, tree_dir: VfsTreeDir, config: ProducerConfig) -> None:
        self._config = config
        self._tree_dir = tree_dir

        self._messages = MessagesSet()
        self._message_to_file: dict[str, vfs.FileLike] = {}
        self._logger = self.logger.getChild(f"{self._tree_dir.path}")

    @classmethod
    async def from_config(
        cls, resources, vfs_config: VfsStructureConfig, arg, tree_dir: VfsTreeDir
    ):
        if vfs_config.producer_config is None:
            raise TgmountError(f"Missing producer config: {tree_dir.path}")

        return VfsTreePlainDir(tree_dir, vfs_config.producer_config)

    # @measure_time(logger_func=print)
    async def produce(self):
        self._logger.info(f"Producing...")

        self._messages = await self._config.get_messages()

        self._logger.info(f"Producing from {len(self._messages)} messages...")

        self._message_to_file = {
            m: await self._config.produce_file(m) for m in self._messages
        }

        if len(self._message_to_file) > 0:
            await self._tree_dir.put_content(list(self._message_to_file.values()))

        # self._config.message_source.subscribe(self.update)
        self._config.message_source.event_new_messages.subscribe(
            self.update_new_messages
        )

        self._config.message_source.event_removed_messages.subscribe(
            self.update_removed_messages
        )

    async def update_new_messages(self, source, new_messages: Set[Message]):

        self._logger.info(
            f"update_new_messages({list(map(lambda m: m.id, new_messages))})"
        )

        if len(new_messages) == 0:
            return

        new_messages_set = await self._config.apply_filters(Set(new_messages))

        new_files: list[vfs.FileLike] = [
            await self._config.produce_file(m) for m in new_messages_set
        ]

        self._message_to_file.update(
            {
                **{m: f for m, f in zip(new_messages_set, new_files)},
            }
        )

        if len(new_files):
            await self._tree_dir.put_content(new_files)

    async def update_removed_messages(self, source, removed_messages: Set[Message]):
        self._logger.info(
            f"update_removed_messages({list(map(lambda m: m.id, removed_messages))})"
        )

        removed_files = [
            self._message_to_file[m]
            for m in removed_messages
            if m in self._message_to_file
        ]

        for f in removed_files:
            await self._tree_dir.remove_content(f)
