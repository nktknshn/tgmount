import logging
from typing import Any, Awaitable, Callable, Generic, Optional, Protocol, Set, TypeVar

import telethon
from tgmount import vfs

from tgmount.tgclient.files_source import TelegramFilesSource, get_downloadable_item
from tgmount.tgclient import guards

from ._factory import CacheFactoryProto
from .reader import CacheBlockReaderWriter

logger = logging.getLogger("tgmount-cache")
Message = telethon.tl.custom.Message


class FilesSourceCaching(
    # CachingDocumentsStorageProto[CacheBlockReaderWriter]
):
    def __init__(
        self,
        source: TelegramFilesSource,
        *,
        document_cache_factory: CacheFactoryProto[CacheBlockReaderWriter],
    ) -> None:
        self._source = source
        self._document_cache_factory = document_cache_factory

    def file_content(self, message: guards.MessageDownloadable):
        item = get_downloadable_item(message)

        async def read_func(handle: Any, off: int, size: int) -> bytes:
            return await self.item_read_function(message, off, size)

        fc = vfs.FileContent(size=item.size, read_func=read_func)

        return fc

    async def item_read_function(
        self,
        message: guards.MessageDownloadable,
        offset: int,
        limit: int,
    ) -> bytes:

        cache = await self._document_cache_factory.get_cache(message)

        data = await cache.read_range(
            self._source.get_read_function(message), offset, limit
        )

        return data
