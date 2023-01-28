from typing import Mapping, Sequence, TypeVar

from tgmount import vfs
from tgmount.tgclient.message_types import MessageProto
from tgmount.tgclient.messages_collection import MessagesCollection, messages_difference

from tgmount.tgmount.vfs_tree import VfsTreeDir
from tgmount.tgmount.vfs_tree_producer_types import (
    VfsTreeProducerConfig,
    VfsTreeProducerProto,
)

from tgmount.util.func import snd, fst
from .logger import module_logger as _logger


class VfsTreeProducerPlainDir(VfsTreeProducerProto):
    """Produces a directory with a list of files"""

    logger = _logger.getChild(f"VfsTreeProducerPlainDir")

    def __init__(
        self,
        tree_dir: VfsTreeDir,
        config: VfsTreeProducerConfig,
    ) -> None:
        self._config = config
        self._tree_dir = tree_dir

        self._message_to_file: dict[int, vfs.FileLike] = {}

        self._logger = self.logger.getChild(
            f"{self._tree_dir.path}", suffix_as_tag=True
        )

    @classmethod
    async def from_config(
        cls,
        resources,
        vfs_config: VfsTreeProducerConfig,
        arg: Mapping,
        tree_dir: VfsTreeDir,
    ):

        return VfsTreeProducerPlainDir(tree_dir, vfs_config)

    async def add_items_to_vfs_tree(self, items: Sequence[vfs.DirContentItem]):
        await self._tree_dir.put_content(
            items,
        )

    async def remove_items_from_vfs_dir(self, items: Sequence[vfs.DirContentItem]):
        for f in items:
            await self._tree_dir.remove_content(f)

    # @measure_time(logger_func=print)
    async def produce(self):

        _messages = MessagesCollection.from_iterable(await self._config.get_messages())

        self._logger.debug(f"Producing from {len(_messages)} messages...")

        self._message_to_file = {
            m.id: await self._config.produce_file(m) for m in _messages
        }

        if len(self._message_to_file) > 0:
            await self.add_items_to_vfs_tree(list(self._message_to_file.values()))

        self._config.message_source.event_new_messages.subscribe(
            self.update_new_messages
        )

        self._config.message_source.event_removed_messages.subscribe(
            self.update_removed_messages
        )

        self._config.message_source.event_edited_messages.subscribe(
            self.update_edited_messages
        )

    async def update_edited_messages(
        self,
        source,
        old_messages: list[MessageProto],
        edited_messages: list[MessageProto],
    ):
        """ """
        self._logger.debug(
            f"update_edited_messages(old_messages={list(map(lambda m: m.id, old_messages))})"
        )

        if len(old_messages) == 0:
            return

        old_messages_dict = {
            m.id: m for m in old_messages if m.id in self._message_to_file.keys()
        }

        edited_messages_dict = {m.id: m for m in edited_messages}

        filtered_edited_messages = await self._config.apply_filters(edited_messages)

        removed_messages, new_messages, common_messages = messages_difference(
            list(old_messages_dict.values()), filtered_edited_messages
        )

        old_updated_files = [
            self._message_to_file[old.id] for (old, new) in common_messages
        ]

        removed_files = [self._message_to_file[m.id] for m in removed_messages]

        new_files: list[vfs.FileLike] = [
            await self._config.produce_file(m) for m in new_messages
        ]

        updated_files: list[vfs.FileLike] = [
            await self._config.produce_file(new) for old, new in common_messages
        ]

        update_content_dict = {
            old_file.name: new_file
            for old_file, new_file in zip(old_updated_files, updated_files)
        }

        self._message_to_file.update(
            {
                **{m.id: f for m, f in zip(new_messages, new_files)},
                **{m.id: f for m, f in zip(map(snd, common_messages), updated_files)},
            }
        )

        for m in removed_messages:
            del self._message_to_file[m.id]

        if len(removed_files):
            await self.remove_items_from_vfs_dir(removed_files)

        if len(new_files):
            await self.add_items_to_vfs_tree(new_files)

        if len(updated_files):
            await self.update_items_in_vfs_tree(
                {
                    item.name: (msg, item)
                    for (msg, item) in zip(map(fst, common_messages), old_updated_files)
                },
                {
                    item.name: (msg, item)
                    for (msg, item) in zip(map(snd, common_messages), updated_files)
                },
                update_content_dict,
            )

    async def update_items_in_vfs_tree(
        self,
        old_files: Mapping[str, tuple[MessageProto, vfs.FileLike]],
        new_files: Mapping[str, tuple[MessageProto, vfs.FileLike]],
        update_content_dict: Mapping[str, vfs.FileLike],
    ):
        await self._tree_dir.update_content(update_content_dict)

    async def update_new_messages(self, source, new_messages: list[MessageProto]):

        self._logger.debug(
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
            # await self._tree_dir.put_content(new_files)

    async def update_removed_messages(
        self, source, removed_messages: list[MessageProto]
    ):
        self._logger.debug(
            f"update_removed_messages({list(map(lambda m: m.id, removed_messages))})"
        )

        removed_files = [
            self._message_to_file[m.id]
            for m in removed_messages
            if m.id in self._message_to_file
        ]

        # for f in removed_files:
        await self.remove_items_from_vfs_dir(removed_files)
        # await self._tree_dir.remove_content(f)
