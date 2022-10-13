from typing import TypedDict
from tgmount.tgclient.client_types import (
    IterDownloadProto,
    ListenerNewMessages,
    ListenerRemovedMessages,
)
from tgmount.tgclient.message_types import AudioProto, DocumentProto, VoiceProto
from tgmount.tgclient.types import (
    InputDocumentFileLocation,
    InputPhotoFileLocation,
    TotalListTyped,
)

from tgmount.tgclient.guards import MessageWithDocument

from telethon import events, hints, types
import aiofiles
import os

from tgmount.util import map_none, none_fallback, random_int, none_fallback_lazy
from .mocked_message import (
    MockedDocument,
    MockedFile,
    MockedForward,
    MockedMessage,
    MockedMessageWithDocument,
    MockedSender,
)


EntityId = str | int


class StorageFile:
    def __init__(
        self,
        id: int,
        file_bytes: bytes,
        access_hash: int,
        file_reference: bytes,
        file_name: str | None = None,
        attributes: list[types.TypeDocumentAttribute] | None = None,
    ) -> None:
        self.id = id
        self._bytes: bytes = file_bytes
        self._file_name = file_name
        self._attributes = attributes
        self._access_hash = access_hash
        self._file_reference = file_reference
        self._size = len(file_bytes)

    @property
    def size(self):
        return self._size

    @property
    def name(self):
        return self._file_name

    @property
    def file_bytes(self):
        return self._bytes

    def get_document(self) -> MockedDocument:

        attributes = none_fallback(self._attributes, [])

        if self._file_name is not None:
            attributes.append(types.DocumentAttributeFilename(self._file_name))

        return MockedDocument(
            id=self.id,
            size=self._size,
            access_hash=self._access_hash,
            file_reference=self._file_reference,
            attributes=attributes,
        )


class Files:
    def __init__(self) -> None:
        self._files: dict[int, StorageFile] = {}
        self._last_id = 0

    def _next_id(self):
        self._last_id += 1
        return self._last_id

    def _new_access_hash(self):
        return random_int(100000)()

    def _new_file_reference(self) -> bytes:
        return bytes([random_int(255)() for _ in range(0, 32)])

    def add_file(
        self,
        file_bytes: bytes,
        file_name: str | None = None,
        attributes: list[types.TypeDocumentAttribute] | None = None,
    ):
        file = StorageFile(
            id=self._next_id(),
            file_bytes=file_bytes,
            file_name=file_name,
            file_reference=self._new_file_reference(),
            access_hash=self._new_access_hash(),
            attributes=attributes,
        )

        self._files[file.id] = file

        return file

    def get_file(self, id: int) -> StorageFile | None:
        return self._files.get(id)


import telethon
from tgmount import tglog


class FileWithText(TypedDict, total=False):
    file: str
    text: str | None
    image: bool | None


class StorageEntityMixin:
    _storage: "MockedTelegramStorage"
    _entity_id: EntityId

    async def text_messages(self, texts: list[str]) -> list[MockedMessage]:
        res = []
        for text in texts:
            res.append(await self.message(text=text))
        return res

    async def files(
        self, files: list[str | FileWithText]
    ) -> list[MockedMessageWithDocument]:
        res = []
        for f in files:
            if isinstance(f, str):
                res.append(await self.document(file=f))
            else:
                res.append(
                    await self.document(
                        file=f["file"],
                        text=f.get("text"),
                        image=bool(f.get("image")),
                    )
                )
        return res

    async def message(
        self,
        text: str | None = None,
        put=True,
        sender: str | MockedSender | None = None,
        forward: str | MockedForward | None = None,
    ) -> MockedMessage:
        msg = self._storage.init_message(self._entity_id)

        if sender is not None:
            msg.sender = (
                MockedSender(username=sender, id=None)
                if isinstance(sender, str)
                else sender
            )
        if forward is not None:
            if isinstance(forward, MockedForward):
                msg.forward = forward
            else:
                msg.forward = MockedForward.create(None, forward)

        if text is not None:
            msg.text = text

        if put:
            await self._storage.put_message(msg)

        return msg

    async def document(
        self,
        file: str | DocumentProto,
        *,
        sender: str | MockedSender | None = None,
        forward: str | MockedForward | None = None,
        file_name: str | bool = True,
        text: str | None = None,
        audio=False,
        image=False,
        video=False,
        put=True,
        voice_note=False,
        video_note=False,
        gif=False,
    ) -> MockedMessageWithDocument:
        msg = await self.message(put=False, sender=sender, forward=forward)

        if isinstance(file, str):
            storage_file = await self._storage.create_storage_file(file, file_name)
            msg.document = storage_file.get_document()

            if image:
                msg.document.attributes.append(
                    telethon.types.DocumentAttributeImageSize(100, 100)
                )
        else:
            storage_file = self._storage.files.get_file(file.id)

            if storage_file is None:
                raise Exception(f"Missing file with id {file.id}")

            msg.document = file

        msg.text = text
        msg.file = MockedFile.from_filename(storage_file.name)

        if audio:
            msg.audio = msg.document

        if gif:
            msg.gif = msg.document

        if video:
            msg.video = msg.document

        if voice_note:
            msg.voice = msg.document

        if video_note:
            msg.video_note = msg.document

        if put:
            await self._storage.put_message(msg)

        return msg

    async def audio_file_message(
        self,
        file: str,
        performer: str | None,
        title: str | None,
        duration: int,
        text: str | None = None,
        file_name: str | bool = True,
        sender: str | MockedSender | None = None,
        put=True,
    ):
        msg = await self.document(
            file, file_name=file_name, text=text, audio=True, sender=sender, put=False
        )
        msg.file.performer = performer
        msg.file.title = title
        msg.file.duration = duration

        if put:
            await self._storage.put_message(msg)

        return msg


class StorageEntity(StorageEntityMixin):
    def __init__(self, storage: "MockedTelegramStorage", entity: EntityId) -> None:
        self._storage: MockedTelegramStorage = storage
        self._messages = []
        self._entity_id = entity
        self._chat_id = hash(entity)
        self._last_message_id = 0

    @property
    def entity_id(self):
        return self._entity_id

    @property
    def chat_id(self):
        return self._chat_id

    def init_message(self):
        return MockedMessage(
            message_id=self.get_new_message_id(),
            chat_id=self.chat_id,
        )

    def get_new_message_id(self):
        self._last_message_id += 1
        return self._last_message_id

    async def add_message(
        self,
        message: MockedMessage
        # message_text: str | None = None,
        # storage_file: Optional["StorageFile"] = None,
    ) -> MockedMessage:

        self._messages.append(message)

        return message

    async def delete_messages(self, message_ids: list[int]):
        entity_messages = []

        for msg in self._messages:
            if msg.id in message_ids:
                continue
            entity_messages.append(msg)

        self._messages = entity_messages

    @property
    def messages(self) -> TotalListTyped:
        return self._messages


class MockedTelegramStorage:
    _logger = tglog.getLogger("MockedTelegramStorage()")

    def __init__(self) -> None:
        self._entities: dict[EntityId, StorageEntity] = {}
        self._entity_by_id: dict[int, StorageEntity] = {}

        self._files_cache: dict[str, bytes] = {}
        self._files = Files()

        self._subscriber_per_entity_new: dict[EntityId, list[ListenerNewMessages]] = {}

        self._subscriber_per_entity_removed: dict[
            EntityId, list[ListenerRemovedMessages]
        ] = {}

    @property
    def files(self):
        return self._files

    def _create_entity(self, entity: EntityId) -> StorageEntity:
        return StorageEntity(self, entity)

    def get_entity(self, entity: EntityId) -> StorageEntity:
        if entity not in self._entities:
            self._entities[entity] = self._create_entity(entity)
            self._entity_by_id[hash(entity)] = self._entities[entity]

        return self._entities[entity]

    def _get_subscribers(
        self, entity: EntityId
    ) -> tuple[list[ListenerNewMessages], list[ListenerRemovedMessages]]:
        return self._subscriber_per_entity_new.get(
            entity, []
        ), self._subscriber_per_entity_removed.get(entity, [])

    def subscribe_new_messages(self, listener: ListenerNewMessages, chats):
        subs = self._subscriber_per_entity_new.get(chats, [])
        subs.append(listener)
        self._subscriber_per_entity_new[chats] = subs

    def subscribe_removed_messages(self, listener: ListenerRemovedMessages, chats):
        subs = self._subscriber_per_entity_removed.get(chats, [])
        subs.append(listener)
        self._subscriber_per_entity_removed[chats] = subs

    # async def create_message(
    #     self, entity: str, message=None, file=None, force_document=False
    # ) -> MockedMessage:
    #     pass

    async def _read_file(self, file_path: str) -> bytes:

        if file_path in self._files_cache:
            return self._files_cache[file_path]

        async with aiofiles.open(file=file_path, mode="rb") as f:
            self._files_cache[file_path] = await f.read()
            return self._files_cache[file_path]

    async def _add_file(self, file_bytes: bytes, file_name: str):
        return self._files.add_file(file_bytes=file_bytes, file_name=file_name)

    async def create_storage_file(
        self,
        file: str,
        file_name: str | bool = True,
    ):
        file_bytes = await self._read_file(file)

        if isinstance(file_name, bool) and file_name is True:
            _file_name = os.path.basename(file)
        elif isinstance(file_name, bool) and file_name is False:
            _file_name = None
        else:
            _file_name = file_name

        storage_file = self._files.add_file(
            file_bytes,
            file_name=_file_name,
        )

        return storage_file

    def init_message(self, entity: EntityId):
        ent = self.get_entity(entity)

        return ent.init_message()

    async def put_message(self, message: MockedMessage):

        ent = self._entity_by_id[message.chat_id]
        message = await ent.add_message(message)

        for s in self._get_subscribers(ent.entity_id)[0]:
            await s(events.NewMessage.Event(message))

        return message

    async def add_message(
        self,
        entity: EntityId,
        message_text: str | None = None,
        file: str | None = None,
        file_name: str | bool = True,
        audio: bool = False,
        voice: bool = False,
        # force_document=False,
    ):

        storage_file = None
        _file_name = None

        ent = self.get_entity(entity)

        if file is not None:
            storage_file = await self.create_storage_file(file, file_name)

        message = MockedMessage(
            message_id=ent.get_new_message_id(),
            chat_id=ent.chat_id,
            message=message_text,
            document=storage_file.get_document() if storage_file is not None else None,
        )

        if storage_file is not None:
            message.file = MockedFile(
                name=_file_name,
                mime_type=map_none(
                    _file_name, lambda n: telethon.utils.mimetypes.guess_type(n)[0]
                ),
                ext=map_none(_file_name, lambda n: os.path.splitext(n)[0]),
                performer=None,
            )

        message = await ent.add_message(message)

        for s in self._get_subscribers(entity)[0]:
            await s(events.NewMessage.Event(message))

        return message

    async def delete_messages(self, entity: str, msg_ids: list[int]):
        ent = self.get_entity(entity)
        await ent.delete_messages(msg_ids)

        for s in self._get_subscribers(entity)[1]:
            await s(events.MessageDeleted.Event(msg_ids, entity))

    async def get_messages(self, entity: str) -> TotalListTyped:
        ent = self.get_entity(entity)
        return ent.messages

    def iter_download(
        self,
        *,
        input_location: InputPhotoFileLocation | InputDocumentFileLocation,
        offset: int,
        request_size: int,
        limit: int,
        file_size: int,
    ) -> IterDownloadProto:
        file = self._files.get_file(input_location.id)

        if file is None:
            raise Exception(f"Missing file with id {input_location.id}")

        self._logger.debug(
            f"iter_download({file.id}, size={file._size}, offset={offset}, limit={limit})"
        )

        file_bytes = file.file_bytes
        _range = file_bytes[offset : offset + limit * request_size]
        # _range = file_bytes[offset : offset + limit * request_size]
        chunks = []

        while len(_range):
            chunks.append(_range[:request_size])
            _range = _range[request_size:]

        return IterDownload(chunks)


class IterDownload(IterDownloadProto):
    def __init__(self, chunks: list[bytes]) -> None:
        self._iter = iter(chunks)

    def __aiter__(self) -> "IterDownloadProto":
        return self

    async def __anext__(self) -> bytes:
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration
