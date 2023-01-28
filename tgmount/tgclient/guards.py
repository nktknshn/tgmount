import abc
from typing import Any, ClassVar, Optional, Protocol, TypeGuard, TypeVar

from .message_types import (
    DocumentProto,
    MessageProto,
    FileProto,
    PhotoProto,
    ForwardProto,
    ReactionsProto,
)


T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)


class ClassWithGuard(Protocol[T_co]):
    # __name__: ClassVar[str]

    @staticmethod
    @abc.abstractmethod
    def guard(msg: MessageProto) -> TypeGuard[T_co]:
        ...


class WithTryGetMethodProto(Protocol[T_co]):
    @classmethod
    @abc.abstractmethod
    def try_get(cls, message: MessageProto) -> Optional[T_co]:
        ...


class TryGetFromGuard(WithTryGetMethodProto[T], Protocol):
    @classmethod
    @abc.abstractmethod
    def try_get(cls: ClassWithGuard[T], message: MessageProto) -> Optional[T]:
        if cls.guard(message):
            return message


"""
Message.media
The media sent with this message if any (such as
        photos, videos, documents, gifs, stickers, etc.).

Message.file
Returns a `File <telethon.tl.custom.file.File>` wrapping the
        `photo` or `document` in this message. If the media type is different
        (polls, games, none, etc.), this property will be `None`.
"""


class TelegramMessage(MessageProto, Protocol):
    @staticmethod
    def guard(msg: Any) -> TypeGuard["TelegramMessage"]:
        return MessageProto.guard(msg)


class MessageForwarded(TelegramMessage, Protocol):
    forward: ForwardProto

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageForwarded"]:
        return TelegramMessage.guard(msg) and msg.forward is not None


class MessageDownloadable(
    TelegramMessage,
    TryGetFromGuard["MessageDownloadable"],
    Protocol,
):
    """Message that has a document or a compressed photo attached.  `MessageWithDocument` or `MessageWithCompressedPhoto`"""

    file: FileProto

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageDownloadable"]:
        return TelegramMessage.guard(msg) and (
            MessageWithDocument.guard(msg) or MessageWithCompressedPhoto.guard(msg)
        )

    @staticmethod
    def document_or_photo_id(
        m: "MessageProto",
    ) -> int:
        if (_id := MessageDownloadable.try_document_or_photo_id(m)) is not None:
            return _id

        raise ValueError(f"incorrect input message: {m}")

    @staticmethod
    def try_document_or_photo_id(
        m: "MessageProto",
    ) -> int | None:
        if MessageWithDocument.guard(m):
            return m.document.id
        elif MessageWithCompressedPhoto.guard(m):
            return m.photo.id

        return None

    @staticmethod
    def filename(message: "MessageDownloadable"):
        return f"{message.id}_document"


class MessageWithReactions(
    MessageProto,
    TryGetFromGuard["MessageWithReactions"],
    Protocol,
):
    reactions: ReactionsProto

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageWithReactions"]:
        return msg.reactions is not None


class MessageWithDocument(
    MessageDownloadable,
    TryGetFromGuard["MessageWithDocument"],
    Protocol,
):
    document: DocumentProto
    file: FileProto

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageWithDocument"]:
        return TelegramMessage.guard(msg) and msg.document is not None


class MessageWithoutDocument(
    MessageDownloadable,
    TryGetFromGuard["MessageWithoutDocument"],
    Protocol,
):
    document: None
    file: None

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageWithoutDocument"]:
        return TelegramMessage.guard(msg) and msg.document is None


class FileWithName(FileProto, Protocol):
    name: str


class MessageWithFilename(
    MessageDownloadable,
    TryGetFromGuard["MessageWithFilename"],
    Protocol,
):
    """message with document with file name"""

    file: FileWithName
    document: DocumentProto

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
    Protocol,
):
    """message with compressed image"""

    file: FileProto
    photo: PhotoProto

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageWithCompressedPhoto"]:
        return (
            TelegramMessage.guard(msg)
            and PhotoProto.guard(msg.photo)
            and not MessageWithSticker.guard(msg)
        )

    @staticmethod
    def filename(msg: "MessageWithCompressedPhoto"):
        return f"{msg.id}_photo.jpeg"


class MessageWithDocumentImage(
    MessageDownloadable,
    TryGetFromGuard["MessageWithDocumentImage"],
    Protocol,
):
    """message with uncompressed image"""

    file: FileProto
    document: DocumentProto

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageWithDocumentImage"]:
        return (
            TelegramMessage.guard(msg)
            and msg.document is not None
            and DocumentProto.guard_document_image(msg.document)
            and not msg.sticker
        )

    @staticmethod
    def filename(msg: "MessageWithDocumentImage"):
        return f"{msg.id}_{msg.file.name}"


class MessageWithZip(
    MessageWithFilename,
    TryGetFromGuard["MessageWithZip"],
    Protocol,
):
    """message with a zip file"""

    file: FileProto
    document: DocumentProto

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
    Protocol,
):
    """stickers"""

    file: FileProto
    document: DocumentProto

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageWithSticker"]:
        return TelegramMessage.guard(msg) and msg.sticker is not None

    @staticmethod
    def filename(message: "MessageWithSticker"):
        return f"{message.id}_{message.file.name}"


class MessageWithKruzhochek(
    MessageDownloadable,
    TryGetFromGuard["MessageWithKruzhochek"],
    Protocol,
):
    # class MessageWithCircle(Message):
    """circles"""

    file: FileProto
    document: DocumentProto

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageWithKruzhochek"]:
        return TelegramMessage.guard(msg) and bool(msg.video_note)

    @staticmethod
    def filename(message: "MessageWithKruzhochek"):
        return f"{message.id}_circle{message.file.ext}"


class MessageWithVideo(
    MessageDownloadable,
    TryGetFromGuard["MessageWithVideo"],
    Protocol,
):
    """circles, video documents, stickers, gifs"""

    file: FileProto
    document: DocumentProto

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
    Protocol,
):
    """video files"""

    file: FileProto
    document: DocumentProto

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
    Protocol,
):
    """uncompressed video documents"""

    file: FileProto
    document: DocumentProto

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
    Protocol,
):
    """stickers, gifs"""

    file: FileProto
    document: DocumentProto

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
    Protocol,
):
    """voices and music"""

    document: DocumentProto

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageWithAudio"]:
        return TelegramMessage.guard(msg) and bool(msg.audio) or bool(msg.voice)


class MessageWithVoice(
    MessageDownloadable,
    TryGetFromGuard["MessageWithVoice"],
    Protocol,
):
    file: FileProto
    document: DocumentProto

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageWithVoice"]:
        return TelegramMessage.guard(msg) and bool(msg.voice)

    @staticmethod
    def filename(message: "MessageWithVoice"):
        return f"{message.id}_voice{message.file.ext}"


class MessageWithMusic(
    MessageDownloadable,
    TryGetFromGuard["MessageWithMusic"],
    Protocol,
):
    """message with document audio tacks (without voices)"""

    file: FileProto
    document: DocumentProto

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
    Protocol,
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
    def filename(message: "MessageWithText"):
        return f"{message.id}_message.txt"


class MessageWithOtherDocument(
    MessageWithFilename,
    TryGetFromGuard["MessageWithOtherDocument"],
    Protocol,
):
    """other documents with file name"""

    document: DocumentProto

    @staticmethod
    def guard(msg: Any) -> TypeGuard["MessageWithOtherDocument"]:

        return (
            # TelegramMessage.guard(msg)
            # and msg.document is not None
            MessageWithFilename.guard(msg)
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
    def filename(message: "MessageWithOtherDocument"):
        return MessageWithFilename.filename(message)
