from abc import abstractmethod
import logging
import os
from typing import Iterable, Optional, TypeVar

import telethon
from telethon.tl.custom import Message

from tgmount import fs, vfs
from tgmount.tg_vfs.tree.helpers.music import group_by_performer
from tgmount.tgclient import (
    MessageSourceProto,
)
from tgmount.tgclient.guards import MessageWithMusic
from tgmount.tgclient.message_source import (
    MessageSourceSubscribable,
    Set,
)

from .tgmount_root_producer_types import (
    ProducerConfig,
    MessagesSet,
)
from .types import CreateRootResources
from .vfs_structure import VfsStructure
from .vfs_structure_plain import VfsStructureProducerPlain
from .vfs_structure_types import VfsStructureProducerProto
from .util import sets_difference


logger = logging.getLogger("MessageByUserSource")


class TelegramMessageSourceSimple(MessageSourceSubscribable):
    def __init__(self, messages=None) -> None:
        super().__init__()
        self._messages: Optional[MessagesSet] = messages
        self._logger = logger

    async def get_messages(self) -> MessagesSet:
        if self._messages is None:
            self._logger.error(f"Messages are not initiated yet")
            return Set()

        return self._messages

    async def set_messages(self, messages: MessagesSet):
        if self._messages is None:
            self._messages = messages

        removed, new, common = sets_difference(self._messages, messages)

        if len(removed) > 0 or len(new) > 0:
            self._messages = messages
            await self.notify(self._messages)


class VfsStructureProducerBase(VfsStructureProducerProto):
    """ """

    MessageSource = TelegramMessageSourceSimple
    VfsStructure = VfsStructure

    def __init__(
        self,
        producer_config: ProducerConfig,
    ) -> None:

        self._producer_config = producer_config

        self._vfs_structure: VfsStructure = self.VfsStructure()

        self._by_path_source: dict[str, MessageSourceSubscribable] = {}
        self._by_path_vfs_structure: dict[str, VfsStructure] = {}

        self._logger = logger

    async def plain_content(self, message_source: MessageSourceSubscribable):
        return await VfsStructureProducerPlain.create(
            message_source=message_source,
            factory=self._producer_config.factory,
        ).produce_vfs_struct()

    async def set_root_content(self, message_source: MessageSourceSubscribable):
        await self._vfs_structure.put("/", await self.plain_content(message_source))

    async def add_subfolder(
        self, path: str, message_source: MessageSourceSubscribable | list[Message]
    ):

        if isinstance(message_source, list):
            message_source = self.MessageSource(message_source)

        self._by_path_source[path] = message_source

        subfolder_vfs_structure = await self.plain_content(message_source)
        self._by_path_vfs_structure[path] = subfolder_vfs_structure
        await self._vfs_structure.put(path, subfolder_vfs_structure)

    @abstractmethod
    async def build_vfs_struct(self) -> VfsStructure:
        ...

    async def produce_vfs_struct(self) -> VfsStructure:
        """
        Produce initial VFS structure
        """
        await self.build_vfs_struct()

        self._producer_config.message_source.subscribe(self.on_update)

        return self._vfs_structure

    async def source_messages(self):
        return await self._producer_config.message_source.get_messages()

    @abstractmethod
    async def on_update(self, source: MessageSourceProto, messages: Iterable[Message]):
        pass
        # by_performer, no_performer = group_by_performer(
        #     filter(MessageWithMusic.guard, messages),
        #     minimum=self._minimum,
        # )

        # old_dirs = Set(self._by_path_source.keys())

        # current_dirs = Set(by_performer.keys())

        # removed_dirs, new_dirs, common_dirs = sets_difference(old_dirs, current_dirs)

        # # we need to update FS
        # await self._vfs_structure.update_vfs(
        #     fs.FileSystemOperationsUpdate(removed_dir_contents=list(removed_dirs))
        # )

        # for new_dir in new_dirs:
        #     #
        #     pass

        # # notify sources
        # for dirname in common_dirs:
        #     _source = self._by_path_source[dirname]
        #     await _source.set_messages(Set(by_performer[dirname]))

        # await self._no_performer_source.set_messages(Set(no_performer))

    @staticmethod
    @abstractmethod
    def from_config(
        resources: CreateRootResources, producer: ProducerConfig, arg: dict
    ) -> "VfsStructureProducerProto":
        ...
