from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import overload
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


class GlobalIds:
    STARTING_ID = 0

    def __init__(self) -> None:
        self.ids: dict[str, int] = {}

    def get_new_id(self, idid: str):
        if idid not in self.ids:
            self.ids[idid] = self.STARTING_ID

        res = self.ids[idid]
        self.ids[idid] += 1
        return res


global_ids = GlobalIds()


@dataclass
class MockedReactionEmoji(ReactionEmojiProto):
    emoticon: str


@dataclass
class MockedReactionCount(ReactionCountProto):
    reaction: MockedReactionEmoji
    count: int


class MockedReactions(ReactionsProto):
    def __init__(self, results) -> None:
        self.results = results

    @staticmethod
    def from_dict(reactions: Mapping[str, int]):
        results = []

        for r, c in reactions.items():
            results.append(MockedReactionCount(MockedReactionEmoji(r), c))
        return MockedReactions(results)


@dataclass
class MockedDocument(DocumentProto):
    size: int
    id: int = field(default_factory=random_int(100000))
    access_hash: int = field(default_factory=random_int(100000))
    # They must be cached by the client, along with the origin context where the document/photo object was found, in order to be refetched when the file reference expires.
    file_reference: bytes = field(default_factory=bytes)
    attributes: list = field(default_factory=list)


@dataclass
class MockedForward(ForwardProto):
    from_id: int
    is_channel: bool
    is_group: bool
    from_name: str | None = None

    async def get_chat(self):
        pass

    @overload
    @staticmethod
    def create(
        from_id: int, from_name: str | None, is_channel=False, is_group=False
    ) -> "MockedForward":
        ...

    @overload
    @staticmethod
    def create(
        from_id: None, from_name: str, is_channel=False, is_group=False
    ) -> "MockedForward":
        ...

    @staticmethod
    def create(from_id, from_name, is_channel=False, is_group=False) -> "MockedForward":
        if from_id is None:
            from_id = hash(from_name)
        return MockedForward(from_id, is_channel, is_group, from_name)


class MockedSender(SenderProto):
    def __repr__(self) -> str:
        return f"MockedSender({self.username})"

    def __init__(self, username: str | None, id: int | None) -> None:
        self.username = username
        self.id = hash(username) if id is None else id

    @staticmethod
    def create(id: int | None, username: str | None) -> "MockedSender":
        return MockedSender(username, id)


class MockedFile(FileProto):
    def __repr__(self) -> str:
        return f"MockedFile(name={self.name}, mime_type={self.mime_type})"

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
            ext=map_none(file_name, lambda n: os.path.splitext(n)[1]),
        )


class MockedMessage(MessageProto):
    def __repr__(self) -> str:
        return f"MockedMessage({self.id}, file={map_none(self.file, lambda f: f.name)}, sender={self.sender}, chat_id={self.chat_id}, message='{self.message}')"

    def __init__(
        self,
        *,
        message_id: int = None,
        chat_id: int = None,
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
        self.chat_id: int = chat_id
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
        self.from_id = None

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

    async def get_sender(self) -> SenderProto:
        return self.sender

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document.id if self.document is not None else None,
        }

    def clone(self):
        return deepcopy(self)


from copy import deepcopy


class MockedMessageWithDocument(MockedMessage):
    document: DocumentProto
    file: FileProto
