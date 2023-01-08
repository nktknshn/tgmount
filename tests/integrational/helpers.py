import asyncio
import copy
import os
import threading
from typing import Any, AsyncGenerator, Coroutine, Mapping, TypedDict

import aiofiles.os

import aiofiles
import telethon
from tests.helpers.mocked.mocked_storage import StorageEntity
import tgmount.config as config
import tgmount.tgclient as tg
from tests.integrational.integrational_helpers import DEFAULT_ROOT
from tgmount import tglog, vfs
from tgmount.main.util import read_tgapp_api
from tgmount.tgmount.tgmount_builder import TgmountBuilder
import pytest
from tgmount.tgmount.producers.producer_by_sender import VfsTreeDirBySender

# from tests.integrational.helpers import async_walkdir, create_config, mdict

# import os

from tgmount.util import Timer, none_fallback

Message = telethon.tl.custom.Message
Document = telethon.types.Document
Client = tg.TgmountTelegramClient


TESTING_CHANNEL = "tgmounttestingchannel"

# Props = Mapping
Props = TypedDict(
    "Props",
    debug=bool,
    ev0=threading.Event,
    ev1=threading.Event,
    cfg=config.Config,
)

DEFAULT_CACHES: Mapping = {
    "memory1": {
        "type": "memory",
        "kwargs": {"capacity": "50MB", "block_size": "128KB"},
    }
}


import asyncio


async def concurrentlys(*coros: Coroutine):
    ts = map(asyncio.create_task, coros)

    done, prending = await asyncio.wait(ts, return_when=asyncio.ALL_COMPLETED)

    if len(done) < len(coros):
        pytest.fail(f"some of the coros threw an exception: {done.pop().exception()}")

    return tuple(map(lambda r: r.result(), done))


async def concurrently(coro1: Coroutine, coro2: Coroutine):
    t1 = asyncio.create_task(coro1)
    t2 = asyncio.create_task(coro2)

    done, prending = await asyncio.wait([t1, t2], return_when=asyncio.ALL_COMPLETED)

    if len(done) < 2:
        pytest.fail(f"some of the coros threw an exception: {done.pop().exception()}")

    [res1, res2] = done

    return res1.result(), res2.result()


def create_config(
    *,
    message_sources={"source1": "source1"},
    caches=DEFAULT_CACHES,
    root: Mapping = DEFAULT_ROOT,
) -> config.Config:
    api_id, api_hash = read_tgapp_api()

    _message_sources = {
        k: config.MessageSource(entity=v) for k, v in message_sources.items()
    }

    _caches = {
        k: config.Cache(type=v["type"], kwargs=v["kwargs"]) for k, v in caches.items()
    }

    return config.Config(
        client=config.Client(api_id=api_id, api_hash=api_hash, session="tgfs"),
        message_sources=config.MessageSources(sources=_message_sources),
        caches=config.Caches(_caches),
        root=config.Root(root),
    )


async_listdir = aiofiles.os.listdir


async def async_walkdir(
    path: str,
) -> AsyncGenerator[tuple[str, list[str], list[str]], None]:
    # item: os.DirEntry
    subdirs: list[str] = []
    subfiles: list[str] = []

    for subitem in await aiofiles.os.listdir(path):
        subitem_path = os.path.join(path, subitem)

        if await aiofiles.os.path.isdir(subitem_path):
            subdirs.append(subitem_path)
        elif await aiofiles.os.path.isfile(subitem_path):
            subfiles.append(subitem_path)

    yield path, subdirs, subfiles

    for subdir in subdirs:
        dir_iter = async_walkdir(subdir)
        async for res in dir_iter:
            yield res


class MyTgmountBuilder(TgmountBuilder):
    def __init__(self, client_kwargs={}) -> None:
        super().__init__()
        self._client_kwargs = client_kwargs

    async def create_client(self, cfg: config.Config):
        return await super().create_client(cfg, **self._client_kwargs)


class mdict:
    def __init__(self, root: Mapping) -> None:
        self._root: dict = copy.deepcopy(dict(root))
        self._current_dict = self._root
        self._path = []

    def enter(self, path: str):
        _path = vfs.napp(path, True)
        self._enter_path(_path)
        return self

    def _enter_path(self, path: list[str]):
        for p in path:
            self._enter(p)

        return self

    def _enter(self, key: str | None = None):
        if key is None:
            self._path = []
            self._current_dict = self._root
        else:
            self._path.append(key)
            self._current_dict = self._current_dict[key]
        return self

    def update(self, d: dict, *, at: str | None = None):
        if at is not None:
            self.enter(at)

        self._current_dict.update(copy.deepcopy(d))
        return self

    def go(self):
        pass

    def get(self):
        return self._root
