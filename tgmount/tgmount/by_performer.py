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
from tgmount.tgmount.vfs_structure_producer_base import VfsStructureProducerBase

from .tgmount_root_producer_types import (
    ProducerConfig,
    MessagesSet,
)
from .types import CreateRootResources
from .vfs_structure import VfsStructure
from .vfs_structure_plain import VfsStructureProducerPlain, sets_difference
from .vfs_structure_types import VfsStructureProducerProto

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


class MessageByPerformer(VfsStructureProducerBase):
    """ """

    def __init__(self, producer_config: ProducerConfig, *, minimum=1) -> None:
        super().__init__(producer_config)
        self._minimum = minimum
        self._no_performer_source = self.MessageSource()

    async def build_vfs_struct(self):
        by_performer, no_performer = group_by_performer(
            filter(MessageWithMusic.guard, await self.source_messages()),
            minimum=self._minimum,
        )

        for name, performer_dir_source in by_performer.items():
            self._logger.info(f"Producing for {name}")
            await self.add_subfolder(name, performer_dir_source)

        await self._no_performer_source.set_messages(no_performer)
        await self.set_root_content(self._no_performer_source)

    async def on_update(self, source: MessageSourceProto, messages: Iterable[Message]):

        if self._vfs_structure is None:
            self._logger.error(f"self._vfs_structure has not been initiated yet")
            return

        by_performer, no_performer = group_by_performer(
            filter(MessageWithMusic.guard, messages),
            minimum=self._minimum,
        )

        old_dirs = Set(self._source_by_name.keys())

        current_dirs = Set(by_performer.keys())

        removed_dirs, new_dirs, common_dirs = sets_difference(old_dirs, current_dirs)

        # we need to update FS
        await self._vfs_structure.update(
            fs.FileSystemOperationsUpdate(removed_dir_contents=list(removed_dirs))
        )

        for new_dir in new_dirs:
            #
            user_source = self.create_source(new_dir, Set(by_performer[new_dir]))
            await self.create_performer_vfs_structure(new_dir, user_source)

        # notify sources
        for dirname in common_dirs:
            _source = self._source_by_name[dirname]
            await _source.set_messages(Set(by_performer[dirname]))

        await self._no_performer_source.set_messages(Set(no_performer))

    def iter_sources(self):
        return self._source_by_name.items()

    @property
    def less_source(self):
        return self._no_performer_source

    @staticmethod
    def from_config(
        resources: CreateRootResources, producer: ProducerConfig, arg: dict
    ) -> "VfsStructureProducerProto":
        return MessageByPerformer(
            producer,
            minimum=arg.get("minimum", 1),
        )
