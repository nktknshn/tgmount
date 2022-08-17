from abc import abstractmethod
from typing import Iterable, Optional, Protocol

from telethon.tl.custom import Message

from tgmount import cache, fs, main, tg_vfs, tgclient, util, vfs, zip as z
from tgmount.tgclient.guards import *
from tgmount.util import asyn as async_utils, func, guards


class TgmountProto(Protocol):
    ...


class TgmountBase(TgmountProto):
    def __init__(
        self,
        client: tgclient.TgmountTelegramClient,
        document_cache_factory=cache.CacheFactoryMemory(blocksize=256 * 1024),
    ) -> None:
        self._client = client

        self._messages_source = client
        self._files_source = tgclient.TelegramFilesSource(client)

        self._vfs_root: Optional[vfs.VfsRoot] = None
        self._fs: Optional[fs.FileSystemOperationsUpdatable] = None

        self._caching_source = cache.FilesSourceCaching(
            self._files_source,
            document_cache_factory=document_cache_factory,
        )

        self._files_factory = tg_vfs.FileFactory(self._files_source)
        self._files_factory_cached = tg_vfs.FileFactory(self._caching_source)

    @abstractmethod
    async def vfs_root(self, *args, **kwargs) -> vfs.VfsRoot:
        pass

    @property
    def files_factory(self):
        return self._files_factory

    @property
    def files_factory_cached(self):
        return self._files_factory_cached

    async def mount(self, *args, destination: str, **kwargs):
        await self._build(*args, **kwargs)
        await main.util.mount_ops(self._fs, destination)

    async def _build(self, *args, **kwargs):
        self._vfs_root = await self.vfs_root(*args, **kwargs)
        self._fs = fs.FileSystemOperationsUpdatable(self._vfs_root)
