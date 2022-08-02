from typing import Any, Awaitable, Callable, Optional, Protocol

import telethon
from tgmount import vfs
from tgmount.tgclient import Document, Message


# class SourceUtilsMixin:
#     def get_read_function(
#         self: "DocumentsSourceProto",
#         message: Message,
#         document: Document,
#     ) -> Callable[[int, int], Awaitable[bytes]]:
#         async def _inn(offset: int, limit: int) -> bytes:
#             return await self.document_read_function(message, document, offset, limit)

#         return _inn

#     async def document_to_file_content(
#         self: "DocumentsSourceProto",
#         message: telethon.tl.custom.Message,
#         document: telethon.types.Document,
#     ) -> vfs.FileContent:
#         async def read_func(handle: Any, off: int, size: int) -> bytes:
#             return await self.document_read_function(message, document, off, size)

#         fc = vfs.FileContent(size=document.size, read_func=read_func)

#         return fc
