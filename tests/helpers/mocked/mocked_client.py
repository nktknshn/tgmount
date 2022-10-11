from dataclasses import dataclass, field
import telethon
import tgmount.tgclient as tg
from tgmount.tgclient.client_types import (
    IterDownloadProto,
    ListenerNewMessages,
    ListenerRemovedMessages,
    TgmountTelegramClientReaderProto,
    TgmountTelegramClientWriterProto,
)
from tgmount.tgclient.types import (
    InputDocumentFileLocation,
    InputPhotoFileLocation,
    TotalListTyped,
)
from telethon import events, hints
import random
import aiofiles
import os

from .mocked_message import MockedMessage
from .mocked_storage import MockedTelegramStorage

Message = telethon.tl.custom.Message
Document = telethon.types.Document
Client = tg.TgmountTelegramClient


class MockedClientReader(TgmountTelegramClientReaderProto):
    def __init__(self, storage: MockedTelegramStorage) -> None:
        self._storage = storage

    async def auth(self):
        pass

    def subscribe_new_messages(self, listener: ListenerNewMessages, chats):
        self._storage.subscribe_new_messages(listener=listener, chats=chats)

    def subscribe_removed_messages(self, listener: ListenerRemovedMessages, chats):
        self._storage.subscribe_removed_messages(listener=listener, chats=chats)

    async def get_messages(self, entity, **kwargs) -> TotalListTyped[MockedMessage]:
        return await self._storage.get_messages(entity)

    def iter_download(
        self,
        input_location: InputPhotoFileLocation | InputDocumentFileLocation,
        *,
        offset: int,
        request_size: int,
        limit: int,
        file_size: int,
    ) -> IterDownloadProto:
        return self._storage.iter_download(
            input_location=input_location,
            offset=offset,
            request_size=request_size,
            limit=limit,
            file_size=file_size,
        )


class MockedClientWriter(TgmountTelegramClientWriterProto):
    def __init__(self, storage: MockedTelegramStorage) -> None:
        self._storage = storage

    async def send_message(
        self, entity: str, message=None, file=None, force_document=False
    ) -> Message:
        return await self._storage.add_message(
            entity,
            message_text=message,
            file=file,
            # force_document=force_document,
        )

    async def delete_messages(self, entity: str, *, msg_ids: list[int]):
        return await self._storage.delete_messages(entity, msg_ids=msg_ids)
