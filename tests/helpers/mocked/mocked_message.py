from dataclasses import dataclass, field
import telethon
import tgmount.tgclient as tg

from tgmount.tgclient.message_types import *
from tgmount.tgclient.types import (
    InputDocumentFileLocation,
    InputPhotoFileLocation,
    TotalListTyped,
)
from telethon import events, hints
import random
import aiofiles
import os

from tgmount.util import map_none

# Message = telethon.tl.custom.Message
# Document = telethon.types.Document
Client = tg.TgmountTelegramClient

random_int = lambda max: lambda: int(max * random.random())


@dataclass
class MockedDocument(DocumentProto):
    size: int
    id: int = field(default_factory=random_int(100000))
    access_hash: int = field(default_factory=random_int(100000))
    # They must be cached by the client, along with the origin context where the document/photo object was found, in order to be refetched when the file reference expires.
    file_reference: bytes = field(default_factory=bytes)
    attributes: dict = field(default_factory=dict)


# class MockedFile:
#     def __init__(self, name: str) -> None:
#         self._name = name

#     @property
#     def name(self):
#         return self._name

#     @property
#     def media(self):
#         return None

#     @property
#     def ext(self):
#         return os.path.splitext(self._name)[1]


class MockedSender(SenderProto):
    def __init__(self, username: str | None, id: int | None) -> None:
        self.username = username
        self.id = hash(username) if id is None else id


class MockedFile(FileProto):
    def __init__(
        self,
        name: str | None,
        mime_type: str | None,
        ext: str | None,
        performer: str | None = None,
        title: str | None = None,
        duration: int | None = None,
    ) -> None:
        self.name = name
        self.mime_type = mime_type
        self.ext = ext
        self.performer = performer
        self.title = title
        self.duration = duration

    @staticmethod
    def from_filename(file_name: str | None):
        return MockedFile(
            name=file_name,
            mime_type=map_none(
                file_name, lambda n: telethon.utils.mimetypes.guess_type(n)[0]
            ),
            ext=map_none(file_name, lambda n: os.path.splitext(n)[0]),
        )


class MockedMessage(MessageProto):
    def __repr__(self) -> str:
        return f"MockedMessage({self.id})"

    def __init__(
        self,
        *,
        message_id: int,
        chat_id: int,
        peer_id=None,
        message=None,
        username=None,
        document: MockedDocument | None = None,
        file=None,
        # storage_file: "StorageFile" | None = None,
        media=None,
        photo=None,
        voice=None,
        sticker=None,
        video_note=None,
        audio=None,
        video=None,
        forward=None,
        gif=None,
        reactions=None,
    ) -> None:

        # super().__init__(message_id)
        self.post = True

        # self.message = message
        self._text = message

        self.id = message_id
        self.chat_id = chat_id
        # self._sender.id =
        self.sender: MockedSender | None = None
        self.file = file

        # self._document = MockedDocument() if file else None
        self.document = document
        self.peer_id = peer_id
        self.media = media
        self.photo = photo
        self.audio = audio
        self.voice = voice
        self.sticker = sticker
        self.video_note = video_note
        self.video = video
        self.gif = gif
        self.forward = forward
        self.reactions = reactions

        self.storage_document = None

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, text):
        self._text = text

    @property
    def message(self):
        return self._text

    @message.setter
    def message(self, text):
        self._text = text

    # @property
    # def id(self):
    #     return self._message_id

    # @property
    # def peer_id(self):
    #     return self._peer_id

    # @property
    # def chat_id(self):
    #     return self._chat_id

    # @property
    # def post(self):
    #     return None

    # @property
    # def file(self):
    #     return self._file

    # @property
    # def media(self):
    #     return self._media

    # @property
    # def forward(self):
    #     return self._forward

    # @property
    # def photo(self):
    #     return self._photo

    # @property
    # def audio(self):
    #     return self._audio

    # @property
    # def voice(self):
    #     return self._voice

    # @property
    # def sticker(self):
    #     return self._sticker

    # @property
    # def video_note(self):
    #     return self._video_note

    # @property
    # def video(self):
    #     return self._video

    # @property
    # def gif(self):
    #     return self._gif

    # @property
    # def document(self):
    #     return self._document

    # @property
    # def action(self):
    #     return None

    # @property
    # def reactions(self):
    #     return self._reactions

    async def get_sender(self) -> SenderProto:
        return self.sender

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document.id if self.document is not None else None,
        }


class MockedMessageWithDocument(MockedMessage):
    document: DocumentProto
    file: FileProto
