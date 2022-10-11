import abc
from typing import Any, Optional, Protocol, TypeGuard, TypeVar

import telethon
from telethon import types
from telethon.tl.custom import Message
from telethon.tl.custom.file import File

from .types import Document


T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)


def add_hash(msg: Message):
    if type(msg).__hash__ is None:
        type(msg).__hash__ = lambda self: (
            self.id,
            MessageDownloadable.try_document_or_photo_id(self),
        ).__hash__()
    return msg


class ClassWithGuard(Protocol[T_co]):
    @staticmethod
    @abc.abstractmethod
    def guard(msg: Message) -> TypeGuard[T_co]:
        ...


class WithTryGetMethodProto(Protocol[T_co]):
    @classmethod
    @abc.abstractmethod
    def try_get(cls, message: Message) -> Optional[T_co]:
        ...


class TryGetFromGuard(WithTryGetMethodProto[T]):
    @classmethod
    @abc.abstractmethod
    def try_get(cls: ClassWithGuard[T], message: Message) -> Optional[T]:
        if cls.guard(message):
            return message


def get_attribute(doc: Document, attr_cls) -> Optional[Any]:
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


class TelegramMessage(Message):
    @staticmethod
    def guard(msg: Any) -> TypeGuard["TelegramMessage"]:
        return isinstance(msg, Message)


class MessageForwarded(TelegramMessage):
    forward: telethon.tl.custom.forward.Forward

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageForwarded"]:
        return TelegramMessage.guard(msg) and msg.forward is not None


class MessageDownloadable(
    TelegramMessage,
    TryGetFromGuard["MessageDownloadable"],
):
    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageDownloadable"]:
        return TelegramMessage.guard(msg) and (
            MessageWithDocument.guard(msg) or MessageWithCompressedPhoto.guard(msg)
        )

    @staticmethod
    def document_or_photo_id(
        m: "MessageDownloadable",
    ) -> int:
        if (_id := MessageDownloadable.try_document_or_photo_id(m)) is not None:
            return _id

        raise ValueError(f"incorrect input message: {m}")

    @staticmethod
    def try_document_or_photo_id(
        m: "MessageDownloadable",
    ) -> int | None:
        if MessageWithDocument.guard(m):
            return m.document.id
        elif MessageWithCompressedPhoto.guard(m):
            return m.photo.id

        return None

    @staticmethod
    def filename(message: "MessageDownloadable"):
        return f"{message.id}_document"


# class MessageWithReactions(Message):
#     reactions: telethon.tl.custom.forward.Forward

#     @staticmethod
#     def guard(msg: Message) -> TypeGuard["MessageForwarded"]:
#         return msg.forward is not None


class MessageWithDocument(
    MessageDownloadable,
    TryGetFromGuard["MessageWithDocument"],
):
    document: Document

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageWithDocument"]:
        return TelegramMessage.guard(msg) and msg.document is not None


class FileWithName(File):
    name: str


class MessageWithFilename(
    MessageDownloadable,
    TryGetFromGuard["MessageWithFilename"],
):
    """message with document with file name"""

    file: FileWithName
    document: Document

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageWithFilename"]:
        return (
            TelegramMessage.guard(msg)
            and msg.file is not None
            and msg.file.name is not None
        )

    @staticmethod
    def filename(message: "MessageWithFilename"):
        return f"{message.id}_{message.file.name}"


class MessageWithCompressedPhoto(
    MessageDownloadable,
    TryGetFromGuard["MessageWithCompressedPhoto"],
):
    """message with compressed image"""

    file: File
    photo: telethon.types.Photo

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageWithCompressedPhoto"]:
        return (
            TelegramMessage.guard(msg)
            and isinstance(msg.photo, telethon.types.Photo)
            and not MessageWithSticker.guard(msg)
        )

    @staticmethod
    def filename(msg: "MessageWithCompressedPhoto"):
        return f"{msg.id}_photo.jpeg"


# MessageDownloadable = MessageWithDocument | MessageWithCompressedPhoto


class MessageWithDocumentImage(
    MessageDownloadable,
    TryGetFromGuard["MessageWithDocumentImage"],
):
    """message with uncompressed image"""

    file: File
    document: Document

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageWithDocumentImage"]:
        return (
            TelegramMessage.guard(msg)
            and msg.document is not None
            and get_attribute(msg.document, types.DocumentAttributeImageSize)
            is not None
            and not msg.sticker
        )

    @staticmethod
    def filename(msg: "MessageWithDocumentImage"):
        return f"{msg.id}_{msg.file.name}"


class MessageWithZip(
    MessageWithFilename,
    TryGetFromGuard["MessageWithZip"],
):
    """message with a zip file"""

    file: File
    document: Document

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageWithZip"]:
        return (
            TelegramMessage.guard(msg)
            and msg.document is not None
            and msg.file is not None
            and msg.file.name is not None
            and msg.file.name.endswith(".zip")
        )

    @staticmethod
    def filename(message: "MessageWithZip"):
        return MessageWithFilename.filename(message)


class MessageWithSticker(
    MessageDownloadable,
    TryGetFromGuard["MessageWithSticker"],
):
    """stickers"""

    file: File
    document: Document

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageWithSticker"]:
        return TelegramMessage.guard(msg) and msg.sticker is not None

    @staticmethod
    def filename(message: "MessageWithSticker"):
        return f"{message.id}_{message.file.name}"


class MessageWithKruzhochek(
    MessageDownloadable,
    TryGetFromGuard["MessageWithKruzhochek"],
):
    # class MessageWithCircle(Message):
    """circles"""

    file: File
    document: Document

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageWithKruzhochek"]:
        return TelegramMessage.guard(msg) and bool(msg.video_note)

    @staticmethod
    def filename(message: "MessageWithKruzhochek"):
        return f"{message.id}_circle{message.file.ext}"


class MessageWithVideo(
    MessageDownloadable,
    TryGetFromGuard["MessageWithVideo"],
):
    """circles, video documents, stickers, gifs"""

    file: File
    document: Document

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageWithVideo"]:

        return TelegramMessage.guard(msg) and (
            bool(msg.video) or MessageWithVideoDocument.guard(msg) or bool(msg.gif)
        )

    @staticmethod
    def filename(message: "MessageWithVideo"):
        return f"{message.id}_video{message.file.ext}"


class MessageWithVideoFile(
    MessageDownloadable,
    TryGetFromGuard["MessageWithVideoFile"],
):
    """video files"""

    file: File
    document: Document

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageWithVideoFile"]:
        return (
            TelegramMessage.guard(msg)
            and MessageWithVideo.guard(msg)
            and not MessageWithKruzhochek.guard(msg)
            and not MessageWithAnimated.guard(msg)
            # and not MessageWithVideoDocument.guard(msg)
        )

    @staticmethod
    def filename(message: "MessageWithVideoFile"):
        if message.file.name is not None:
            return f"{message.id}_{message.file.name}"
        else:
            return f"{message.id}_video{message.file.ext}"


class MessageWithVideoDocument(
    MessageDownloadable,
    TryGetFromGuard["MessageWithVideoDocument"],
):
    """uncompressed video documents"""

    file: File
    document: Document

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageWithVideoDocument"]:
        return (
            TelegramMessage.guard(msg)
            and MessageWithDocument.guard(msg)
            and msg.file is not None
            and msg.file.mime_type is not None
            and msg.file.mime_type.startswith("video")
            and not bool(msg.video)
        )


class MessageWithAnimated(
    MessageDownloadable,
    TryGetFromGuard["MessageWithAnimated"],
):
    """stickers, gifs"""

    file: File
    document: Document

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageWithAnimated"]:

        return TelegramMessage.guard(msg) and msg.gif is not None

    @staticmethod
    def filename(message: "MessageWithAnimated"):
        if message.file.name:
            return f"{message.id}_{message.file.name}"
        else:
            return f"{message.id}_gif{message.file.ext}"


class MessageWithAudio(
    MessageDownloadable,
    TryGetFromGuard["MessageWithAudio"],
):
    """voices and music"""

    document: Document

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageWithAudio"]:
        return TelegramMessage.guard(msg) and bool(msg.audio) or bool(msg.voice)


class MessageWithVoice(
    MessageDownloadable,
    TryGetFromGuard["MessageWithVoice"],
):
    file: File
    document: Document

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageWithVoice"]:
        return TelegramMessage.guard(msg) and bool(msg.voice)

    @staticmethod
    def filename(message: "MessageWithVoice"):
        return f"{message.id}_voice{message.file.ext}"


class MessageWithMusic(
    MessageDownloadable,
    TryGetFromGuard["MessageWithMusic"],
):
    """message with document audio tacks (without voices)"""

    file: File
    document: Document

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageWithMusic"]:
        return TelegramMessage.guard(msg) and msg.audio is not None

    @staticmethod
    def filename(message: "MessageWithMusic"):
        if message.file.name:
            return f"{message.id}_{message.file.name}"
        else:
            return f"{message.id}_music{message.file.ext}"


class MessageWithText(
    TelegramMessage,
    TryGetFromGuard["MessageWithText"],
):
    text: str

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageWithText"]:
        return (
            TelegramMessage.guard(msg)
            and isinstance(msg.text, str)
            and len(msg.text) > 0
        )

    @staticmethod
    def filename(message: "MessageWithVoice"):
        return f"{message.id}_message.txt"


class MessageWithOtherDocument(
    MessageDownloadable,
    TryGetFromGuard["MessageWithOtherDocument"],
):
    """other documents with file name"""

    document: Document

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageWithOtherDocument"]:

        return (
            TelegramMessage.guard(msg)
            and msg.document is not None
            and not (
                MessageWithDocumentImage.guard(msg)
                or MessageWithCompressedPhoto.guard(msg)
                or MessageWithVideo.guard(msg)
                or MessageWithAudio.guard(msg)
                or MessageWithSticker.guard(msg)
                or MessageWithAnimated.guard(msg)
                or MessageWithVideoDocument.guard(msg)
            )
        )

    @staticmethod
    def filename(message: "MessageWithVoice"):
        return MessageWithFilename.filename(message)
