from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, fields
from typing import Any, Optional, Type, TypeGuard

import telethon
from telethon import events, types

from tgmount import config, fs, main, tg_vfs, tgclient, vfs
from tgmount.cache import CacheFactory
from tgmount.fs.util import measure_time
from tgmount.tg_vfs import classifier
from tgmount.tg_vfs.classifier import ClassifierBase
from tgmount.tgclient import TelegramMessageSource, guards
from tgmount.tgclient.message_source import TelegramMessageSourceProto
from tgmount.util import col, compose_guards
from tgmount.vfs.util import MyLock

from .error import TgmountError
from .logger import logger
from .producers import TreeProducer
from .types import CreateRootResources, Filter, TgmountRoot
from .wrappers import DirContentWrapper

Message = telethon.tl.custom.Message


class Tgmount:
    FileSystemOperations: Type[
        fs.FileSystemOperationsUpdatable
    ] = fs.FileSystemOperationsUpdatable

    def __init__(
        self,
        *,
        client: tgclient.TgmountTelegramClient,
        message_sources: Mapping[str, TelegramMessageSource],
        root: TgmountRoot,
        file_factory: tg_vfs.FileFactoryProto,
        filters: Mapping[str, Type[Filter]],
        producers: Mapping[str, Type[TreeProducer]],
        caches: Mapping[str, CacheFactory],
        cached_sources: Mapping[str, tg_vfs.FileFactoryProto],
        wrappers: Mapping[str, Type[DirContentWrapper]],
        classifier: ClassifierBase,
        mount_dir: Optional[str] = None,
    ) -> None:
        # self._client
        self._client = client
        self._mount_dir: Optional[str] = mount_dir
        self._message_sources: Mapping[str, TelegramMessageSource] = message_sources
        self._root: TgmountRoot = root

        self._caches = caches
        self._cached_sources = cached_sources

        self._file_factory = file_factory
        self._filters: Mapping[str, Type[Filter]] = filters
        self._wrappers = wrappers
        self._producers = producers
        self._classifier = classifier
        self._fs = None

    @property
    def client(self):
        return self._client

    @property
    def caches(self):
        return self._caches

    @property
    def fs(self) -> fs.FileSystemOperationsUpdatable | None:
        return self._fs

    @measure_time(logger_func=logger.info)
    async def copy_sources(self):
        return {
            k: TelegramMessageSourceProto.from_messages(await v.get_messages())
            for k, v in self._message_sources.items()
        }

    @measure_time(logger_func=logger.info)
    async def build_root(self) -> vfs.VfsRoot:
        return vfs.root(
            await self._root(
                CreateRootResources(
                    file_factory=self._file_factory,
                    sources=await self.copy_sources(),
                    filters=self._filters,
                    producers=self._producers,
                    caches=self._cached_sources,
                    wrappers=self._wrappers,
                    classifier=self._classifier,
                )
            )
        )

    @measure_time(logger_func=logger.info)
    async def update(
        self,
        event: events.NewMessage.Event | events.MessageDeleted.Event,
        messages: list[Message],
    ):

        messages = list(filter(guards.MessageDownloadable.guard, messages))

        if len(messages) == 0:
            return

        if self.fs is None:
            return
            # raise TgmountError(f"FileSystemOperations has not been created yet.")

        root = await self.build_root()

        async with self.fs._update_lock:
            await self.fs.update_root(root)

    async def create_fs(self):
        logger.info(f"Building root...")

        root = await self.build_root()

        self._fs = self.FileSystemOperations(root)

    async def mount(
        self,
        *,
        destination: Optional[str] = None,
        debug_fuse=False,
        min_tasks=10,
    ):
        await self.create_fs()

        mount_dir = destination if destination is not None else self._mount_dir

        if mount_dir is None:
            raise TgmountError(f"missing destination")

        # main.cleanup = self._fs.invalidate_all

        logger.info(f"Mounting into {mount_dir}")
        await main.util.mount_ops(
            self._fs,
            mount_dir=mount_dir,
            min_tasks=min_tasks,
            debug=debug_fuse,
        )
