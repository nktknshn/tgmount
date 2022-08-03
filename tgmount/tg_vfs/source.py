from typing import Any, Awaitable, Callable, Optional, Protocol, TypeVar, overload

import telethon
from telethon.errors import FileReferenceExpiredError

import logging
from tgmount import vfs
from tgmount.tgclient import (
    TgmountTelegramClient,
    Message,
    InputDocumentFileLocation,
)
from tgmount.tgclient import TypeInputFileLocation
from tgmount.tgclient.search.filtering.guards import (
    MessageWithDocument,
    MessageWithMusic,
    MessageWithPhoto,
    MessageWithVideo,
)
from .util import BLOCK_SIZE, split_range
from telethon.tl.custom.file import File
from ._source import (
    TelegramFilesSourceBase,
    ItemReadFunctionAsync,
    SourceItem,
    SourceItemPhoto,
    SourceItemDocument,
)

logger = logging.getLogger("tgclient")

InputSourceItem = telethon.types.Photo | telethon.types.Document

T = TypeVar("T")


class FileContentProvider(Protocol):
    def file_content(
        self, message: Message, input_item: InputSourceItem
    ) -> vfs.FileContent:
        ...


class ContentFunc:
    @overload
    def content(
        self: FileContentProvider,
        message: MessageWithDocument,
    ) -> vfs.FileContent:
        ...

    @overload
    def content(
        self: FileContentProvider,
        message: MessageWithPhoto,
    ) -> vfs.FileContent:
        ...

    @overload
    def content(
        self: FileContentProvider,
        message: MessageWithVideo,
    ) -> vfs.FileContent:
        ...

    @overload
    def content(
        self: FileContentProvider,
        message: MessageWithMusic,
    ) -> vfs.FileContent:
        ...

    def content(
        self: FileContentProvider,
        message: MessageWithPhoto
        | MessageWithDocument
        | MessageWithVideo
        | MessageWithMusic,
    ) -> vfs.FileContent:
        if MessageWithPhoto.guard(message):
            return self.file_content(message, message.photo)
        elif MessageWithDocument.guard(message):
            return self.file_content(message, message.document)

        raise ValueError("incorret input message")


class TelegramFilesSource(
    TelegramFilesSourceBase[InputSourceItem],
    ContentFunc,
):
    def __init__(
        self,
        client: TgmountTelegramClient,
        request_size: int = BLOCK_SIZE,
    ) -> None:
        self.client = client
        self.items_file_references: dict[int, bytes] = {}
        self.request_size = request_size

    def _item_to_inner_object(self, input_item: InputSourceItem) -> SourceItem:
        if isinstance(input_item, telethon.types.Photo):
            item = SourceItemPhoto(input_item)
        else:
            item = SourceItemDocument(input_item)

        return item

    def file_content(
        self, message: Message, input_item: InputSourceItem
    ) -> vfs.FileContent:

        item = self._item_to_inner_object(input_item)

        async def read_func(handle: Any, off: int, size: int) -> bytes:
            return await self.item_read_function(message, input_item, off, size)

        fc = vfs.FileContent(size=item.size, read_func=read_func)

        return fc

    def get_read_function(
        self,
        message: Message,
        input_item: InputSourceItem,
    ) -> Callable[[int, int], Awaitable[bytes]]:
        async def _inn(offset: int, limit: int) -> bytes:
            return await self.item_read_function(message, input_item, offset, limit)

        return _inn

    async def item_read_function(
        self,
        message: Message,
        input_item: InputSourceItem,
        offset: int,
        limit: int,
    ) -> bytes:
        item: SourceItem = self._item_to_inner_object(input_item)

        return await self._item_read_function(message, item, offset, limit)

    async def _get_item_input_location(self, item: SourceItem) -> TypeInputFileLocation:
        return item.input_location(
            self._get_item_file_reference(item),
        )

    def _get_item_file_reference(self, item: SourceItem) -> bytes:
        return self.items_file_references.get(
            item.id,
            item.file_reference,
        )

    def _set_item_file_reference(self, item: SourceItem, file_reference: bytes):
        self.items_file_references[item.id] = file_reference

    async def _update_item_file_reference(
        self, message: Message, item: SourceItem
    ) -> TypeInputFileLocation:
        refetched_msg: Message
        [refetched_msg] = await self.client.get_messages(
            message.chat_id, ids=[message.id]
        )

        if not isinstance(refetched_msg, telethon.tl.custom.Message):
            logger.error(f"refetched_msg isnt a Message")
            logger.error(f"refetched_msg={refetched_msg}")
            raise ValueError(f"refetched_msg isnt a Message")

        if refetched_msg.document is None:
            raise ValueError(f"missing document")

        self._set_item_file_reference(item, refetched_msg.document.file_reference)

        return await self._get_item_input_location(item)

    async def _retrieve_file_chunk(
        self,
        input_location: TypeInputFileLocation,
        offset: int,
        limit: int,
        document_size: int,
        *,
        request_size=BLOCK_SIZE,
    ) -> bytes:

        # XXX adjust request_size
        ranges = split_range(offset, limit, request_size)
        result = bytes()

        # if random() > 0.9:
        #     raise FileReferenceExpiredError(None)

        # request_size = (
        #     request_size
        #     if (offset + request_size) <= document_size
        #     else document_size - offset
        # )

        # if offset + request_size > document_size:
        #     offset = document_size - 0

        async for chunk in self.client.iter_download(
            input_location,
            offset=ranges[0],
            request_size=request_size,
            limit=len(ranges) - 1,
            file_size=document_size,
        ):
            logger.debug(f"chunk = {len(chunk)} bytes")
            result += chunk

        return result[offset - ranges[0] : offset - ranges[0] + limit]

    async def _item_read_function(
        self,
        message: Message,
        item: SourceItem,
        offset: int,
        limit: int,
    ) -> bytes:

        logger.debug(
            f"TelegramFilesSource._item_read_function(Message(id={message.id},chat_id={message.chat_id}), item({message.file.name}, {item.id}, offset={offset}, limit={limit})"  # type: ignore
        )

        input_location = await self._get_item_input_location(item)

        try:
            chunk = await self._retrieve_file_chunk(
                input_location,
                offset,
                limit,
                item.size,
                request_size=self.request_size,
            )
        except FileReferenceExpiredError:
            logger.debug(
                f"FileReferenceExpiredError was caught. file_reference for msg={item.id} needs refetching"
            )

            input_location = await self._update_item_file_reference(message, item)

            chunk = await self._retrieve_file_chunk(
                input_location,
                offset,
                limit,
                item.size,
                request_size=self.request_size,
            )
        logger.debug(
            f"TelegramFilesSource.document_read_function() = {len(chunk)} bytes"
        )
        return chunk


""" 
https://core.telegram.org/api/files
"""


# async def document_to_file_content(
#     message: telethon.tl.custom.Message,
#     item: T,
#     document_read_function: ItemReadFunctionAsync,
# ) -> vfs.FileContent:
#     async def read_func(handle: Any, off: int, size: int) -> bytes:
#         return await document_read_function(message, document, off, size)

#     fc = vfs.FileContent(size=item.size, read_func=read_func)

#     return fc
