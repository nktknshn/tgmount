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


class MockedTgmountBuilderBase(TgmountBuilder):
    TelegramClient = MockedClientReader

    def __init__(self, storage: MockedTelegramStorage) -> None:
        self._storage = storage

    async def create_client(self, cfg: config.Config, **kwargs):
        return self.TelegramClient(self._storage)


async def main_function(
    *, mnt_dir: str, cfg: config.Config, debug: bool, storage: MockedTelegramStorage
):

    tglog.init_logging(debug)
    test_logger = tglog.getLogger("main_test1")

    tglog.getLogger("FileSystemOperations()").setLevel(logging.ERROR)
    logging.getLogger("telethon").setLevel(logging.DEBUG)

    test_logger.debug("Building...")
    builder = MockedTgmountBuilderBase(storage=storage)

    test_logger.debug("Creating...")
    tgm = await builder.create_tgmount(cfg)

    test_logger.debug("Auth...")
    await tgm.client.auth()

    test_logger.debug("Creating FS...")
    await tgm.create_fs()

    test_logger.debug("Returng FS")

    await mount_ops(tgm.fs, mount_dir=mnt_dir, min_tasks=10)


async def run_test(mount_coro, test_coro):
    mount_task = asyncio.create_task(mount_coro)
    test_task = asyncio.create_task(test_coro)

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
    debug: bool,
):
    await run_test(
        main_function(mnt_dir=mnt_dir, cfg=cfg, storage=storage, debug=debug),
        test_func(),
    )


class TgmountIntegrationContext:
    MockedTelegramStorage = MockedTelegramStorage
    MockedClientWriter = MockedClientWriter

    def __init__(self, mnt_dir: str, default_config=None) -> None:
        self._mnt_dir = mnt_dir

        self._default_config = none_fallback(default_config, create_config())
        self._storage = self.create_storage()
        self._client = self.create_client()

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

    def _path(self, path: str) -> str:
        return vfs.path_join(self._mnt_dir, path)

    async def listdir(self, path: str, full_path=False) -> list[str]:

        return [
            vfs.path_join(path, f) if full_path else f
            for f in await async_listdir(self._path(path))
        ]

    async def listdir_len(self, path: str) -> int:
        return len(await self.listdir(path))

    async def listdir_set(self, path: str, full_path=False) -> set[str]:
        return set(await self.listdir(path, full_path))

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
        cfg_or_root: config.Config | Mapping,
        debug=False,
    ):
        await _run_test(
            handle_mount(self.mnt_dir)(test_func),
            mnt_dir=self.mnt_dir,
            cfg=cfg_or_root
            if isinstance(cfg_or_root, config.Config)
            else self.create_config(cfg_or_root),
            storage=self.storage,
            debug=debug,
        )


async def read_bytes(path: str):
    async with aiofiles.open(path, "rb") as f:
        return await f.read()


# class TgmountIntegrationTest(TgmountIntegrationContext, abc.ABC):
#     MockedTelegramStorage = MockedTelegramStorage
#     MockedClientWriter = MockedClientWriter

#     @classmethod
#     async def run_test(cls, mnt_dir: str, caplog):
#         await cls(mnt_dir, caplog).run()

#     def __init__(self, mnt_dir: str, caplog) -> None:
#         self._caplog = caplog

#         self._root = self.get_root()
#         self._storage = self.create_storage()
#         self._client = self.create_client()
#         self._cfg = self.create_config()

#     @abstractmethod
#     def get_root(self) -> Mapping:
#         ...

#     @abstractmethod
#     async def prepare_storage(self, storage: MockedTelegramStorage):
#         pass

#     @abstractmethod
#     async def test(self, storage: MockedTelegramStorage, client: MockedClientWriter):
#         pass

#     async def _test(self):
#         await self.test(self._storage, self._client)

#     async def run(self, debug=True):

#         await self.prepare_storage(self._storage)

#         await _run_test(
#             handle_mount(self._mnt_dir)(self._test),
#             mnt_dir=self._mnt_dir,
#             cfg=self._cfg,
#             storage=self._storage,
#             debug=debug,
#         )
