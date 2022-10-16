from abc import abstractmethod
import abc
import asyncio
from collections.abc import Awaitable, Callable
import logging
import os
from typing import Any, Iterable, Mapping, TypedDict

import aiofiles
import pyfuse3
import pytest
import pytest_asyncio
import tgmount
import tgmount.config as config
from tgmount.config.types import Config
import tgmount.tgclient as tg
from tests.helpers.mocked.mocked_storage import EntityId, MockedTelegramStorage
from tests.helpers.mount import handle_mount
from tgmount import tglog, vfs
from tgmount.main.util import mount_ops
from tgmount.tgmount.builder import TgmountBuilder

from ..helpers.fixtures import mnt_dir
from ..helpers.mocked.mocked_client import MockedClientReader, MockedClientWriter
from ..helpers.mocked.mocked_message import MockedFile, MockedMessage, MockedSender
from .helpers import *
from tgmount.util import none_fallback
from tgmount.tgmount import VfsTreeProducer, TgmountBase


class MockedVfsTreeProducer(VfsTreeProducer):
    async def produce_path(self, tree_dir, path: str, vfs_config, ctx):
        # to test concurrent
        # await asyncio.sleep(0.1)
        return await super().produce_path(tree_dir, path, vfs_config, ctx)


class MockedTgmountBase(TgmountBase):
    VfsTreeProducer = MockedVfsTreeProducer


class MockedTgmountBuilderBase(TgmountBuilder):
    TelegramClient = MockedClientReader
    TgmountBase = MockedTgmountBase

    def __init__(self, storage: MockedTelegramStorage) -> None:
        self._storage = storage

    async def create_client(self, cfg: config.Config, **kwargs):
        return self.TelegramClient(self._storage)


async def main_function(
    *,
    mnt_dir: str,
    cfg: config.Config,
    debug: int,
    storage: MockedTelegramStorage,
):

    # tglog.init_logging(debug_level=debug)

    test_logger = tglog.getLogger("main_test1")
    test_logger.setLevel(debug)

    # tglog.getLogger("FileSystemOperations()").setLevel(logging.ERROR)
    # logging.getLogger("telethon").setLevel(logging.DEBUG)

    test_logger.info("Building...")
    builder = MockedTgmountBuilderBase(storage=storage)

    test_logger.info("Creating resources...")
    tgm = await builder.create_tgmount(cfg)

    test_logger.info("Auth...")
    await tgm.client.auth()

    test_logger.info("Creating FS...")
    await tgm.create_fs()

    test_logger.info("Returng FS")

    await mount_ops(tgm.fs, mount_dir=mnt_dir, min_tasks=10)


async def run_test(mount_coro, test_coro):
    mount_task = asyncio.create_task(mount_coro, name="mount_task")
    test_task = asyncio.create_task(test_coro, name="test_task")

    done, pending = await asyncio.wait(
        [mount_task, test_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    if mount_task in done:
        try:
            done.pop().result()
        except Exception:
            # pytest.fail(f"Mount process finished before test")
            pending.pop().cancel()
            raise
    else:
        done.pop().result()
        pending.pop().cancel()


async def _run_test(
    test_func,
    *,
    mnt_dir: str,
    cfg: config.Config,
    storage: MockedTelegramStorage,
    debug: int,
    main_function=main_function,
):
    await run_test(
        main_function(mnt_dir=mnt_dir, cfg=cfg, storage=storage, debug=debug),
        test_func(),
    )


class TgmountIntegrationContext:
    MockedTelegramStorage = MockedTelegramStorage
    MockedClientWriter = MockedClientWriter

    def __init__(self, mnt_dir: str, *, caplog=None, default_config=None) -> None:
        self._mnt_dir = mnt_dir
        self._caplog = caplog

        self._default_config = none_fallback(default_config, create_config())
        self._storage = self.create_storage()
        self._client = self.create_client()
        self._debug = False
        self.main_function = main_function

    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, value):
        logging_level = (
            logging.DEBUG
            if value is True
            else logging.CRITICAL
            if value is False
            else value
        )
        self._debug = logging_level

        tglog.init_logging(logging_level)

        if self._caplog is not None:
            self._caplog.set_level(self._debug)

    @property
    def storage(self):
        return self._storage

    @property
    def mnt_dir(self):
        return self._mnt_dir

    @property
    def client(self):
        return self._client

    def set_config(self, config: Config):
        self._default_config = config

    def create_config(self, root: Mapping):
        return self._default_config.set_root(root)

    def create_storage(self):
        return self.MockedTelegramStorage()

    def create_client(self):
        return self.MockedClientWriter(storage=self._storage)

    def _path(self, *path: str) -> str:
        return vfs.path_join(self._mnt_dir, *path)

    async def listdir(self, *path: str, full_path=False) -> list[str]:

        return [
            vfs.path_join(*path, f) if full_path else f
            for f in await async_listdir(self._path(*path))
        ]

    async def listdir_len(self, *path: str) -> int:
        return len(await self.listdir(*path))

    async def listdir_set(self, *path: str, full_path=False) -> set[str]:
        return set(await self.listdir(*path, full_path=full_path))

    def walkdir(
        self, *path: str
    ) -> AsyncGenerator[tuple[str, list[str], list[str]], None]:
        return async_walkdir(self._path(*path))

    async def listdir_recursive(self, path: str) -> set[str]:
        res = []

        for dirpath, dirnames, filenames in await async_walkdir(path):
            res.append(dirpath)
            res.extend([vfs.path_join(str(dirpath), str(fn)) for fn in filenames])

        return set(res)

    async def read_text(self, path: str) -> str:
        async with aiofiles.open(self._path(path), "r") as f:
            return await f.read()

    async def read_bytes(self, path: str) -> bytes:
        async with aiofiles.open(self._path(path), "rb") as f:
            return await f.read()

    async def read_texts(self, paths: Iterable[str]) -> list[str] | set[str]:
        res = []
        for p in paths:
            res.append(await self.read_text(p))
        if isinstance(paths, set):
            return set(res)
        return res

    def get_root(self, root_cfg: Mapping) -> Mapping:
        return root_cfg

    def mount_task_root(self, root: Mapping, debug=True):
        return self.mount_task(self.create_config(root), debug=debug)

    def mount_task(self, cfg: config.Config, debug=True):
        return asyncio.create_task(
            main_function(
                mnt_dir=self.mnt_dir,
                cfg=cfg,
                storage=self.storage,
                debug=debug,
            )
        )

    async def run_test(
        self,
        test_func: Callable[[], Awaitable[Any]],
        cfg_or_root: config.Config | Mapping | None = None,
        debug=None,
    ):
        _debug = self.debug
        self.debug = none_fallback(debug, self.debug)

        await _run_test(
            handle_mount(self.mnt_dir)(test_func),
            mnt_dir=self.mnt_dir,
            cfg=self._get_config(cfg_or_root),
            storage=self.storage,
            debug=self.debug,
            main_function=self.main_function,
        )
        self.debug = _debug

    def _get_config(
        self,
        cfg_or_root: config.Config | Mapping | None = None,
    ):
        cfg_or_root = none_fallback(cfg_or_root, self._default_config)

        return (
            cfg_or_root
            if isinstance(cfg_or_root, config.Config)
            else self.create_config(cfg_or_root)
        )

    async def create_tgmount(
        self,
        cfg_or_root: config.Config | Mapping | None = None,
    ) -> tgmount.tgmount.TgmountBase:

        builder = MockedTgmountBuilderBase(storage=self.storage)
        tgm = await builder.create_tgmount(self._get_config(cfg_or_root))

        return tgm


async def read_bytes(path: str):
    async with aiofiles.open(path, "rb") as f:
        return await f.read()
