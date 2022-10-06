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


class VfsTreePlainDir(VfsTreeProducerProto):
    def __init__(self, dir: VfsTreeDir, config: ProducerConfig) -> None:
        self._config = config
        self._dir = dir

        self._messages = MessagesSet()
        self._message_to_file: dict[str, vfs.FileLike] = {}
        self._logger = tglog.getLogger(f"VfsTreePlainDir({self._dir.path})")

    @classmethod
    async def from_config(
        cls, resources, vfs_config: VfsStructureConfig, arg, dir: VfsTreeDir
    ):
        if vfs_config.producer_config is None:
            raise TgmountError(f"Missing producer config: {dir.path}")

        return VfsTreePlainDir(dir, vfs_config.producer_config)

    # @measure_time(logger_func=print)
    async def produce(self):
        self._logger.debug(f"Producing...")

        self._messages = await self._config.get_messages()
        self._message_to_file = {
            m: self._config.factory.file(m) for m in self._messages
        }

        if len(self._message_to_file) > 0:
            await self._dir.put_content(list(self._message_to_file.values()))

        # self._config.message_source.subscribe(self.update)
        self._config.message_source.event_new_messages.subscribe(
            self.update_new_messages
        )

        self._config.message_source.event_removed_messages.subscribe(
            self.update_removed_messages
        )

    async def update_new_messages(self, source, new_messages: list[Message]):
        self._logger.info(
            f"update_new_messages({list(map(lambda m: m.id, new_messages))})"
        )

        new_messages_set = await self._config._apply_filters(Set(new_messages))

        new_files: list[vfs.FileLike] = [
            self._config.factory.file(m) for m in new_messages_set
        ]

        self._message_to_file.update(
            {
                **{m: f for m, f in zip(new_messages_set, new_files)},
            }
        )

        if len(new_files):
            await self._dir.put_content(new_files)

    async def update_removed_messages(self, source, removed_messages: list[Message]):
        self._logger.info(
            f"update_removed_messages({list(map(lambda m: m.id, removed_messages))})"
        )
        removed_files = [self._message_to_file[m] for m in removed_messages]

        for f in removed_files:
            await self._dir.remove_content(f)

    # async def update(self, source, messages: list[Message]):
    #     print(f"updating {self._dir.path}")
    #     messages_set = await self._config.get_messages()

    #     removed_messages, new_messages, common_messages = sets_difference(
    #         self._messages, messages_set
    #     )

    #     removed_files = [self._message_to_file[m] for m in removed_messages]
    #     old_files = [self._message_to_file[m] for m in common_messages]
    #     new_files: list[vfs.FileLike] = [
    #         self._config.factory.file(m) for m in new_messages
    #     ]

    #     self._messages = messages_set
    #     self._message_to_file = {
    #         **{m: f for m, f in zip(new_messages, new_files)},
    #         **{m: f for m, f in zip(common_messages, old_files)},
    #     }

    #     for f in removed_files:
    #         await self._dir.remove_content(f)

    #     if len(new_files):
    #         await self._dir.put_content(new_files)
