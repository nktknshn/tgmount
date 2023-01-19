import mimetypes
import os
import random
from dataclasses import dataclass, field

import asyncio
import aiofiles
import telethon
from tgmount import tglog
import tgmount.tgclient as tg
from telethon import events, hints
from tgmount.tgclient.client_types import (
    IterDownloadProto,
    ListenerEditedMessage,
    ListenerNewMessages,
    ListenerRemovedMessages,
    TgmountTelegramClientReaderProto,
    TgmountTelegramClientWriterProto,
)
from tgmount.tgclient.guards import MessageWithDocument
from tgmount.tgclient.types import (
    InputDocumentFileLocation,
    InputPhotoFileLocation,
    TotalListTyped,
)

from .mocked_message import MockedMessage, MockedMessageWithDocument, MockedSender
from .mocked_storage import EntityId, MockedTelegramStorage

Message = telethon.tl.custom.Message
Document = telethon.types.Document
Client = tg.TgmountTelegramClient


class MockedClientReader(TgmountTelegramClientReaderProto):
    logger = tglog.getLogger("MockedClientReader")

    def __repr__(self) -> str:
        return f"MockedClientReader()"

    def __init__(self, storage: MockedTelegramStorage) -> None:
        self._storage = storage

    async def auth(self):
        pass

    def subscribe_new_messages(self, listener: ListenerNewMessages, chats):
        self._storage.subscribe_new_messages(listener=listener, chats=chats)

    def subscribe_removed_messages(self, listener: ListenerRemovedMessages, chats):
        self._storage.subscribe_removed_messages(listener=listener, chats=chats)

    def subscribe_edited_message(self, listener: ListenerEditedMessage, chats):
        self._storage.subscribe_edited_message(listener=listener, chats=chats)

    async def get_messages(self, entity, **kwargs) -> TotalListTyped[MockedMessage]:
        await asyncio.sleep(0.1)
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
    logger = tglog.getLogger("MockedClientWriter")

    def __init__(self, storage: MockedTelegramStorage, sender=None) -> None:
        self._storage = storage
        self._sender: MockedSender | None = sender

    def sender(self, sender: str | MockedSender):
        return MockedClientWriter(
            self._storage,
            sender if isinstance(sender, MockedSender) else MockedSender(sender, None),
        )

    async def send_message(
        self,
        entity: EntityId,
        message=None,
        file: str | None = None,
    ) -> Message:
        self.logger.info(f"send_message({entity}, {message})")
        return await self._storage.get_entity(entity).message(
            text=message,
            # file=file,
            # force_document=force_document,
        )

    async def send_file(
        self,
        entity: EntityId,
        file: str,
        *,
        caption: str | None = None,
        voice_note: bool = False,
        video_note: bool = False,
        force_document=False,
    ) -> MockedMessageWithDocument:

        video = False

        mtype = mimetypes.guess_type(file)[0]

        if mtype is not None and mtype.startswith("video") and not force_document:
            video = True

        return await self._storage.get_entity(entity).document(
            text=caption,
            file=file,
            voice_note=voice_note,
            video_note=video_note,
            video=video,
            sender=self._sender
            # force_document=force_document,
        )

    async def delete_messages(self, entity: EntityId, *, msg_ids: list[int]):
        return await self._storage.delete_messages(entity, msg_ids=msg_ids)
