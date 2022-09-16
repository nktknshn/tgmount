from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, fields
import logging
from typing import Any, Optional, Type, TypeGuard

import telethon
from telethon import events, types

from tgmount import config, fs, main, tg_vfs, tgclient, tglog, vfs
from tgmount.cache import CacheFactory
from tgmount.fs.util import measure_time
from tgmount.tg_vfs import classifier
from tgmount.tg_vfs.classifier import ClassifierBase
from tgmount.tgclient import TelegramMessageSource, guards
from tgmount.tgclient.message_source import (
    MessageSourceProto,
    MessageSourceProto,
    MessageSourceSubscribableProto,
)
from tgmount.tgmount.filters import FiltersMapping
from tgmount.tgmount.tgmount_root_producer2 import TgmountRootProducer
from tgmount.util import col, compose_guards
from tgmount.vfs.util import MyLock

from .error import TgmountError
from .producers import TreeProducer
from .types import CreateRootResources, Filter, TgmountRoot
from .wrappers import DirContentWrapper
from .vfs_structure import VfsStructureProducerBase

Message = telethon.tl.custom.Message


class Tgmount:
    FileSystemOperations: Type[
        fs.FileSystemOperationsUpdatable
    ] = fs.FileSystemOperationsUpdatable

    logger = tglog.getLogger("TgmountRootProducer")

    def __init__(
        self,
        *,
        client: tgclient.TgmountTelegramClient,
        message_sources: Mapping[str, MessageSourceSubscribableProto],
        root: dict,
        file_factory: tg_vfs.FileFactoryProto,
        filters: FiltersMapping,
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
        self._message_sources: Mapping[
            str, MessageSourceSubscribableProto
        ] = message_sources
        self._root = root

        self._caches = caches
        self._cached_sources = cached_sources

        self._file_factory = file_factory
        self._filters: FiltersMapping = filters
        self._wrappers = wrappers
        self._producers = producers
        self._classifier = classifier
        self._fs = None

        self._updates_pending = False
        self._is_building_root = False

        # logger.setLevel(logging.ERROR)
        self._root_producer = TgmountRootProducer(logger=self.logger)

    @property
    def client(self):
        return self._client

    @property
    def caches(self):
        return self._caches

    @property
    def fs(self) -> fs.FileSystemOperationsUpdatable | None:
        return self._fs

    # @measure_time(logger_func=logger.info)
    # async def copy_sources(self):
    #     return {
    #         k: MessageSourceProto.from_messages(await v.get_messages())
    #         for k, v in self._message_sources.items()
    #     }
    @measure_time(logger_func=logger.info)
    async def build_root(self) -> vfs.VfsRoot:
        producer = VfsStructureProducerBase()

        vfs_struct = await producer.produce_vfs_struct(
            self._root,
            resources=CreateRootResources(
                file_factory=self._file_factory,
                # sources=await self.copy_sources(),
                sources=self._message_sources,
                filters=self._filters,
                producers=self._producers,
                caches=self._cached_sources,
                wrappers=self._wrappers,
                classifier=self._classifier,
            ),
        )

        return vfs.root(vfs_struct.get_dir_content_by_path("/"))

    @measure_time(logger_func=logger.info)
    async def _build_root(self) -> vfs.VfsRoot:
        await self._root_producer.build_root(
            self._root,
            resources=CreateRootResources(
                file_factory=self._file_factory,
                # sources=await self.copy_sources(),
                sources=self._message_sources,
                filters=self._filters,
                producers=self._producers,
                caches=self._cached_sources,
                wrappers=self._wrappers,
                classifier=self._classifier,
            ),
        )

        if not self._root_producer._produced_content:
            raise TgmountError(f"produced_content is None")

        return self._root_producer._produced_content.get_vfs_root()

    @measure_time(logger_func=logger.info)
    async def update(
        self,
        message_source: MessageSourceProto,
        messages: frozenset[Message],
        event: events.NewMessage.Event | events.MessageDeleted.Event,
        *,
        force_build=False,
    ):
        self.logger.info(f"{message_source} {event}")
        if not self._root_producer._produced_content:
            self.logger.error(f"produced_content is None")
            return

        await self._root_producer._produced_content.on_update(message_source)

    @measure_time(logger_func=logger.info)
    async def _update(
        self,
        message_source: MessageSourceProto,
        event: events.NewMessage.Event | events.MessageDeleted.Event,
        messages: list[Message],
        *,
        force_build=False,
    ):

        if self.fs is None:
            return
            # raise TgmountError(f"FileSystemOperations has not been created yet.")

        if not self._is_building_root or force_build:
            self._is_building_root = True

            root = await self.build_root()

            self.logger.info("locking")

            async with self.fs._update_lock:
                await self.fs.update_root(root)

            self.logger.info("unlocked")

            if self._updates_pending:
                self._updates_pending = False
                await self.update(None, [], force_build=True)
            else:
                self._is_building_root = False
        else:
            self._updates_pending = True

    async def create_fs(self):
        self.logger.info(f"Building root...")

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

        self.logger.info(f"Mounting into {mount_dir}")
        await main.util.mount_ops(
            self._fs,
            mount_dir=mount_dir,
            min_tasks=min_tasks,
            debug=debug_fuse,
        )
