from typing import TypeGuard
from telethon.tl.custom import message
from telethon.tl.custom.file import File
from telethon import types
from ...types import (
    Document,
    Message,
    Photo,
)

MessageMedia = (
    types.MessageMediaContact
    | types.MessageMediaDice
    | types.MessageMediaDocument
    | types.MessageMediaGame
    | types.MessageMediaGeo
    | types.MessageMediaGeoLive
    | types.MessageMediaInvoice
    | types.MessageMediaPhoto
    | types.MessageMediaPoll
    | types.MessageMediaUnsupported
    | types.MessageMediaVenue
    | types.MessageMediaWebPage
)


def get_attribute(doc: Document, attr_cls):
    for attr in doc.attributes:
        if isinstance(attr, attr_cls):
            return attr


"""
Message.media
The media sent with this message if any (such as
        photos, videos, documents, gifs, stickers, etc.).

Message.file
Returns a `File <telethon.tl.custom.file.File>` wrapping the
        `photo` or `document` in this message. If the media type is different
        (polls, games, none, etc.), this property will be `None`.
"""


class MessageWithDocument(Message):
    file: File
    document: Document

    @staticmethod
    def guard(msg: Message) -> TypeGuard["MessageWithDocument"]:
        return msg.document is not None


class FileWithName(File):
    name: str


class MessageWithFilename(Message):
    file: FileWithName
    document: Document

    @staticmethod
    def guard(msg: Message) -> TypeGuard["MessageWithFilename"]:
        return msg.file is not None and msg.file.name is not None


class MessageWithPhoto(Message):
    file: File
    photo: Photo

    @staticmethod
    def guard(msg: Message) -> TypeGuard["MessageWithPhoto"]:
        return isinstance(msg.photo, Photo)


class MessageWithVideo(Message):
    file: File
    document: Document

    @staticmethod
    def guard(msg: Message) -> TypeGuard["MessageWithVideo"]:
        return (
            msg.document is not None
            and get_attribute(msg.document, types.DocumentAttributeVideo) is not None
        )


class MessageWithMusic(Message):
    file: File
    document: Document

    @staticmethod
    def guard(msg: Message) -> TypeGuard["MessageWithMusic"]:
        return (
            msg.document is not None
            and get_attribute(
                msg.document,
                types.DocumentAttributeAudio,
            )
            is not None
        )


class MessageWithMedia(Message):
    media: MessageMedia

    @staticmethod
    def guard(msg: Message) -> TypeGuard["MessageWithMedia"]:
        return msg.media is not None


class MessageWithText(Message):
    message: str

    @staticmethod
    def guard(msg: Message) -> TypeGuard["MessageWithText"]:
        return isinstance(msg.message, str) and len(msg.message) > 0
