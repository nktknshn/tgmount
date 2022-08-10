import logging
from typing import Any, Awaitable, Callable, Generic, Optional, Protocol, Set, TypeVar

import telethon
from tgmount import vfs
from tgmount.tg_vfs import TelegramFilesSource
from tgmount.tg_vfs import TelegramFilesSourceBase, SourceItem
from tgmount.tg_vfs.source import (
    ContentFunc,
    FileFunc,
    InputSourceItem,
)
from tgmount.tgclient import Message

from ._factory import CacheFactoryProto
from .reader import CacheBlockReaderWriter

logger = logging.getLogger("tgmount-cache")


class FilesSourceCaching(
    TelegramFilesSourceBase[InputSourceItem],
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

    def file_content(self, message: Message, input_item: InputSourceItem):
        item = self._source._item_to_inner_object(input_item)

        async def read_func(handle: Any, off: int, size: int) -> bytes:
            return await self.item_read_function(message, input_item, off, size)

        fc = vfs.FileContent(size=item.size, read_func=read_func)

        return fc

    async def item_read_function(
        self,
        message: telethon.tl.custom.Message,
        input_item: InputSourceItem,
        offset: int,
        limit: int,
    ) -> bytes:
        item = self._source._item_to_inner_object(input_item)

        cache = await self._document_cache_factory.get_cache(message, item)

        data = await cache.read_range(
            self._source.get_read_function(message, input_item), offset, limit
        )

        return data


# class CachingDocumentsStorage(DocumentsStorageProto, CachingDocumentsStorageProto):
#     def __init__(
#         self,
#         storage: DocumentsStorageProto,
#         document_cache_factory: CacheFactory,
#         documents_caches: dict[DocId, DocumentCacheProto] = {},
#     ) -> None:
#         super().__init__(storage, document_cache_factory, documents_caches)

#     async def document_read_function(
#         self,
#         message: telethon.tl.custom.Message,
#         document: telethon.types.Document,
#         offset: int,
#         limit: int,
#     ) -> bytes:
#         cache = await self._get_cache(message, document)

#         cached_data = await cache.try_read(offset, limit)

#         if cached_data is not None:
#             return cached_data

#         block_offset, block_limit = await cache.get_block_range(offset, limit)

#         data = await self._storage.document_read_function(
#             message, document, block_offset, block_limit
#         )

#         await cache.put_block(block_offset, data)

#         cached_data = await cache.try_read(offset, limit)

#         if cached_data is None:
#             raise CachingDocumentsStorageError(f"cache returned None")

#         return cached_data
