from abc import abstractmethod
from typing import (
    AnyStr,
    Awaitable,
    Callable,
    Generic,
    List,
    Optional,
    Protocol,
    Set,
    TypeVar,
)

import telethon

DocId = int


# C = TypeVar("C")

# CacheFactory = Callable[
#     [
#         telethon.tl.custom.Message,
#         telethon.types.Document,
#     ],
#     Awaitable[C],
# ]
# class CachingDocumentsSourceProto(Generic[C]):
#     def __init__(
#         self,
#         storage: DocumentsSourceProto,
#         document_cache_factory: CacheFactory[C],
#         documents_caches: dict[DocId, C] = {},
#     ) -> None:
#         self._storage = storage
#         self._document_cache_factory = document_cache_factory
#         self._documents_caches: dict[DocId, C] = documents_caches

#     async def _initialize_cache(
#         self,
#         message: telethon.tl.custom.Message,
#         document: telethon.types.Document,
#     ) -> C:
#         self._documents_caches[document.id] = await self._document_cache_factory(
#             message, document
#         )

#         return self._documents_caches[document.id]

#     async def _get_cache(
#         self,
#         message: telethon.tl.custom.Message,
#         document: telethon.types.Document,
#     ) -> C:

#         if document.id in self._documents_caches:
#             return self._documents_caches[document.id]

#         self._documents_caches[document.id] = await self._document_cache_factory(
#             message, document
#         )

#         return self._documents_caches[document.id]


# class CacheBlocksStorageProto(Protocol):
#     blocksize: int

#     async def get(self, block_number: int) -> Optional[bytes]:
#         ...

#     async def put(self, block_number: int, block: bytes):
#         ...

#     def blocks(self) -> Set[int]:
#         ...


# class DocumentCacheProto:
#     async def get_block_range(self, offset: int, size: int) -> BlockRange:
#         raise NotImplementedError()

#     async def is_range_cached(self, offset: int, size: int) -> bool:
#         raise NotImplementedError()

#     async def put_block(self, block_offset: int, data: bytes) -> None:
#         raise NotImplementedError()

#     async def try_read(self, offset: int, size: int) -> Optional[bytes]:
#         raise NotImplementedError()


class CachingDocumentsStorageError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
