import logging
import os
from collections.abc import Awaitable, Callable
from typing import Iterable, Optional, TypeVar

import telethon
from telethon.tl.custom import Message

from tgmount import fs, vfs
from tgmount.tg_vfs.tree.helpers.by_user import group_by_sender
from tgmount.tgclient import (
    MessageSourceProto,
    TelegramMessageSource,
    TgmountTelegramClient,
)
from tgmount.tgclient.message_source import (
    MessageSourceSubscribable,
    MessageSourceSubscribableProto,
    Set,
    TelegramMessageSourceSimple,
)
from tgmount.tgmount.error import TgmountError
from tgmount.util import none_fallback

from .filters import (
    Filter,
    FilterAllMessagesProto,
    FilterFromConfigContext,
    ParseFilter,
)
from .tgmount_root_config_reader import (
    TgmountConfigReader,
    TgmountConfigReader2,
    TgmountConfigReaderWalker,
)
from .tgmount_root_producer_types import (
    CreateRootContext,
    ProducerConfig,
    MessagesSet,
    TgmountRootSource,
    VfsStructureConfig,
)
from .types import CreateRootResources
from .vfs_structure import VfsStructure
from .util import sets_difference
from .vfs_structure_plain import VfsStructureProducerPlain
from .vfs_structure_producer2 import VfsStructureFromConfigProducer
from .vfs_structure_types import (
    FsUpdate,
    VfsStructureProducerProto,
    VfsStructureBaseProto,
)

logger = logging.getLogger("MessageByUserSource")


class ByUser(FilterAllMessagesProto):
    def __init__(self, name: str) -> None:
        self.name = name

    @staticmethod
    def from_config(ext: str, ctx: FilterFromConfigContext, parse_filter: ParseFilter):
        return ByUser(ext)

    async def filter(self, messages: Iterable[Message]) -> list[Message]:
        return [m for m in messages if await get_sender_name(m) == self.name]


UserDirProducer = Callable[[TgmountRootSource], Awaitable[None]]
BuildRootFunction = Callable[
    [
        TgmountRootSource,
        CreateRootResources,
        CreateRootContext,
    ],
    None,
]


async def get_sender_name(m: Message):
    sender = await m.get_sender()
    name = None

    if sender is None:
        return None

    if sender.username:
        name = sender.username

    if name is None:
        name = telethon.utils.get_display_name(sender)

    return name


class MessageByUser(VfsStructureProducerProto):
    """
    Creates updatable VFS structure made of composition of other VFS structures (composition of
    vfs.DirContentProto)

    VFS structure provides vfs.DirContentProto

    Each VFS structure is made from TelegramMessageSourceSimple and subscribed to it

    MessageByUser is subscribed to parent message_source from DirContentProducer

    On update parent message_source notifies MessageByUser

    MessageByUser separates messages by sender

    Notifies corresonding TelegramMessageSourceSimple with its messages

    TelegramMessageSourceSimple notifies subscribed VFS nodes if needed

    VFS nodes updates itself notifying subscribers (file system)
    """

    MessageSource = TelegramMessageSourceSimple
    DEFAULT_SENDER_ROOT_CONFIG = {"filter": "All"}

    def __init__(
        self,
        # produce from config
        producer_config: ProducerConfig,
        *,
        minimum=1,
        resources: CreateRootResources,
        dir_cfg=DEFAULT_SENDER_ROOT_CONFIG,
        root_producer: VfsStructureProducerProto | None = None,
    ) -> None:
        self._minimum = minimum
        self._resources = resources

        self._producer_config = producer_config

        self._source_by_name: dict[str, TelegramMessageSourceSimple] = {}
        self._vfs_structure_by_name: dict[str, VfsStructureBaseProto] = {}

        self._by_producer_path: dict[VfsStructureProducerProto, str] = {}

        self._vfs_structure = VfsStructure()

        self._less_source = TelegramMessageSourceSimple()
        self._dir_cfg = dir_cfg
        self._logger = logger
        self._root_producer = root_producer

    def create_source(self, user_name: str, messages: MessagesSet):
        source = self.MessageSource(messages=messages)
        self._source_by_name[user_name] = source
        return source

    def get_vfs_structure(self) -> VfsStructureBaseProto:
        return self._vfs_structure

    async def on_child_update(
        self, subproducer: "VfsStructureProducerProto", update: FsUpdate
    ):
        if self._root_producer:
            await self._root_producer.on_child_update(
                self, update.prepend_paths(self._by_producer_path[subproducer])
            )

    async def create_user_vfs_structure(
        self,
        name: str,
        username_dir_source: MessageSourceSubscribable,
    ):
        # if self._vfs_structure is None:
        #     self._logger.error(
        #         f"Calling create_vfs_structure before self._vfs_structure was created"
        #     )
        #     return
        user_dir_producer = VfsStructureFromConfigProducer(
            self._dir_cfg, self._resources
        )

        self._by_producer_path[user_dir_producer] = name

        user_dir_producer.subscribe(self.on_child_update)

        await user_dir_producer.produce_vfs_struct(
            CreateRootContext.from_resources(
                self._resources, recursive_source=username_dir_source
            ),
        )

        self._vfs_structure_by_name[name] = user_dir_producer.get_vfs_structure()

        # await self._vfs_structure.put(name, user_vfs_structure, generate_event=True)
        return self._vfs_structure_by_name[name]

    async def produce_vfs_struct(self):
        """
        Produce initial VFS structure
        """

        messages = await self._producer_config.message_source.get_messages()

        by_user, less, nones = await group_by_sender(
            messages,
            minimum=self._minimum,
        )

        for user_name, items in by_user.items():
            self.create_source(user_name, Set(items))

        await self._less_source.set_messages(Set(less))

        for name, username_dir_source in self.iter_sources():
            self._logger.info(f"Producing for {name}")
            # here we need to produce another updatabale VFS structure
            # that is subscribed to username_dir_source
            uvfs = await self.create_user_vfs_structure(name, username_dir_source)
            await self._vfs_structure.put(name, uvfs)

        less_vfs_structure_producer = VfsStructureProducerPlain.create(
            root_producer=self,
            message_source=self._less_source,
            factory=self._producer_config.factory,
            tag=f"less_vfs_structure_producer",
        )

        self._by_producer_path[less_vfs_structure_producer] = "/"

        less_vfs_structure = await less_vfs_structure_producer.produce_vfs_struct()

        await self._vfs_structure.put("/", less_vfs_structure)

        # for path, keys, content in vfs_struct.walk_structure("/"):
        #     self._logger.info(f"{path}: {keys} {content}")

        self._producer_config.message_source.subscribe(self.on_update)

        print(self._producer_config.message_source)

        return self._vfs_structure

    async def on_update(self, source: MessageSourceProto, messages: Iterable[Message]):

        print(f"Received update")

        if self._vfs_structure is None:
            self._logger.error(f"self._vfs_structure has not been initiated yet")
            return

        by_user, less, nones = await group_by_sender(
            messages,
            minimum=self._minimum,
        )

        old_dirs = Set(self._source_by_name.keys())

        removed_dirs, new_dirs, common_dirs = sets_difference(
            old_dirs, Set(by_user.keys())
        )

        for d in removed_dirs:
            await self._vfs_structure.remove_by_path(d)

        for new_dir in new_dirs:
            user_source = self.create_source(new_dir, Set(by_user[new_dir]))
            uvs = await self.create_user_vfs_structure(new_dir, user_source)
            await self._vfs_structure.put(new_dir, uvs, generate_event=True)

        # notify sources
        for dirname in common_dirs:
            _source = self._source_by_name[dirname]
            await _source.set_messages(Set(by_user[dirname]))

        await self._less_source.set_messages(Set(less))

        if self._root_producer:
            await self._root_producer.on_child_update(
                self,
                FsUpdate(
                    update_dir_content=["/"],
                    details=dict(
                        removed_dirs=removed_dirs,
                        new_dirs=new_dirs,
                    ),
                ),
            )
        #    FsUpdate(
        #             update_dir_content=["/"],
        #             details=dict(
        #                 removed_files=[f.name for f in removed_files],
        #                 new_files={f.name: f for f in new_files},
        #             ),
        #         ),

    def iter_sources(self):
        return self._source_by_name.items()

    @property
    def less_source(self):
        return self._less_source

    @staticmethod
    def from_config(
        root_producer: "VfsStructureProducerProto",
        resources: CreateRootResources,
        producer: VfsStructureConfig,
        arg: dict,
    ) -> "VfsStructureProducerProto":

        if producer.producer_config is None:
            raise TgmountError(f"Missing producer_config")

        return MessageByUser(
            producer.producer_config,
            minimum=arg.get("minimum", 1),
            resources=resources,
            dir_cfg=arg.get(
                "sender_root",
                MessageByUser.DEFAULT_SENDER_ROOT_CONFIG,
            ),
            root_producer=root_producer,
        )
