from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Optional, TypeGuard
from dataclasses import dataclass, fields

import telethon
from telethon import events, types

from tgmount import tg_vfs, tgclient, vfs, fs
from tgmount.tgclient import TelegramMessageSource, guards
from tgmount import config
from tgmount.util import col, compose_guards
from tgmount.cache import CacheFactory

from .types import DirWrapper, Filter, TgmountRoot, CreateRootResources, TgmountError
from tgmount import main

Message = telethon.tl.custom.Message


class Tgmount:
    FileSystemOperations: fs.FileSystemOperationsUpdatable = (
        fs.FileSystemOperationsUpdatable
    )

    def __init__(
        self,
        client: tgclient.TgmountTelegramClient,
        message_sources: Mapping[str, TelegramMessageSource],
        root: TgmountRoot,
        file_factory: tg_vfs.FileFactory,
        filters: Mapping[str, Filter],
        caches: Mapping[str, tg_vfs.FileFactory],
        wrappers: Mapping[str, DirWrapper],
        mount_dir: Optional[str] = None,
    ) -> None:
        # self._client
        self._client = client
        self._mount_dir: Optional[str] = mount_dir
        self._message_sources: Mapping[str, TelegramMessageSource] = message_sources
        self._root: TgmountRoot = root
        self._caches = caches
        self._file_factory = file_factory
        self._filters: Mapping[str, Filter] = filters
        self._wrappers = wrappers

    @property
    def client(self):
        return self._client

    async def get_root(self) -> vfs.VfsRoot:
        return vfs.root(
            await self._root(
                CreateRootResources(
                    file_factory=self._file_factory,
                    sources=self._message_sources,
                    filters=self._filters,
                    caches=self._caches,
                    wrappers=self._wrappers,
                )
            )
        )

    async def update(
        self,
        event: events.NewMessage.Event | events.MessageDeleted.Event,
        messages: list[Message],
    ):
        if self._fs is None:
            raise TgmountError(f"FileSystemOperations has not been created yet.")

        messages = list(filter(guards.is_downloadable, messages))

        if len(messages) == 0:
            return

        await self._fs.update_root(
            await self.get_root(),
        )

    async def create_fs(self):
        self._fs = self.FileSystemOperations(await self.get_root())

    async def mount(self, *args, destination: Optional[str] = None, **kwargs):
        await self.create_fs()

        mount_dir = destination if destination is not None else self._mount_dir

        if mount_dir is None:
            raise TgmountError(f"missing destination")

        await main.util.mount_ops(self._fs, mount_dir)
