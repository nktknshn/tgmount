import os
from typing import Mapping, Optional, Type

from tgmount import fs, main, tgclient, tglog, vfs
from tgmount.fs.update import FileSystemOperationsUpdate
from tgmount.tgclient.add_hash import add_hash_to_telegram_message_class
from tgmount.tgclient.client_types import TgmountTelegramClientReaderProto
from tgmount.tgclient.telegram_message_source import TelegramEventsDispatcher
from .vfs_tree_types import (
    TreeEventRemovedItems,
    TreeEventNewItems,
    TreeEventRemovedDirs,
    TreeEventNewDirs,
    TreeEventType,
)
from tgmount.tgmount.vfs_tree_producer import (
    VfsTree,
    VfsTreeProducer,
)
from .vfs_tree_message_source import SourcesProviderAccumulating
from .error import TgmountError
from .tgmount_types import TgmountResources
from tgmount.util import none_fallback
from tgmount import config

add_hash_to_telegram_message_class()


class TelegramMessagesFetcher:
    def __init__(
        self,
        client: TgmountTelegramClientReaderProto,
        cfg: config.MessageSource,
    ) -> None:
        self.client = client
        self.cfg = cfg

    async def fetch(
        self,
    ):
        return await self.client.get_messages(
            self.cfg.entity,
            limit=self.cfg.limit,
        )


class TgmountBase:
    """
    Wraps the application state and all the async initialization, connects all the app parts together

    Connects VfsTree and FilesystemOperations by dispatches events from the virtual tree to FilesystemOperations
    """

    FileSystemOperations: Type[
        fs.FileSystemOperationsUpdatable
    ] = fs.FileSystemOperationsUpdatable

    VfsTreeProducer = VfsTreeProducer

    logger = tglog.getLogger("TgmountBase")

    def __init__(self) -> None:
        pass
