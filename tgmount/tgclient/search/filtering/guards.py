from typing import Any, Iterable, Optional, Type, TypeGuard, TypeVar, overload

import telethon
from telethon import types
from telethon.tl.custom import Message
from telethon.tl.custom.file import File
from telethon.tl.types import TypeDocumentAttribute

from ....util import func
from ...types import Document


from tgmount import util

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


def get_attribute(doc: Document, attr_cls) -> Optional[Any]:
    for attr in doc.attributes:
        if isinstance(attr, attr_cls):
            return attr


def document_or_photo_id(
    m: "MessageDownloadable",
) -> int:
    if MessageWithDocument.guard(m):
        return m.document.id
    elif MessageWithCompressedPhoto.guard(m):
        return m.photo.id

    raise ValueError(f"incorrect input message: {m}")


"""
Message.media
The media sent with this message if any (such as
        photos, videos, documents, gifs, stickers, etc.).

Message.file
Returns a `File <telethon.tl.custom.file.File>` wrapping the
        `photo` or `document` in this message. If the media type is different
        (polls, games, none, etc.), this property will be `None`.
"""


class MessageForwarded(Message):
    forward: telethon.tl.custom.forward.Forward

    @staticmethod
    def guard(msg: Message) -> TypeGuard["MessageForwarded"]:
        return msg.forward is not None

    @staticmethod
    async def group_by_forw(
        forwarded_messages: list["MessageForwarded"],
    ):
        fws = {}

        for m in forwarded_messages:

            chat = await m.forward.get_chat()
            sender = await m.forward.get_sender()
            from_name = m.forward.from_name

            dirname = (
                chat.title
                if chat is not None
                else from_name
                if from_name is not None
                else "None"
            )

            if not dirname in fws:
                fws[dirname] = []

            fws[dirname].append(m)

        return fws


# class MessageWithReactions(Message):
#     reactions: telethon.tl.custom.forward.Forward

#     @staticmethod
#     def guard(msg: Message) -> TypeGuard["MessageForwarded"]:
#         return msg.forward is not None


class MessageWithDocument(Message):
    document: Document

    @staticmethod
    def guard(msg: Message) -> TypeGuard["MessageWithDocument"]:
        return msg.document is not None


class FileWithName(File):
    name: str


class MessageWithFilename(Message):
    """message with document with file name"""

    file: FileWithName
    document: Document

    @staticmethod
    def guard(msg: Message) -> TypeGuard["MessageWithFilename"]:
        return msg.file is not None and msg.file.name is not None

    @staticmethod
    def filename(msg: "MessageWithFilename"):
        return f"{msg.id}_{msg.file.name}"


class MessageWithCompressedPhoto(Message):
    """message with compressed image"""

    file: File
    photo: telethon.types.Photo

    @staticmethod
    def guard(msg: Message) -> TypeGuard["MessageWithCompressedPhoto"]:
        return isinstance(
            msg.photo, telethon.types.Photo
        ) and not MessageWithSticker.guard(msg)

    @staticmethod
    def filename(msg: "MessageWithCompressedPhoto"):
        return f"{msg.id}_photo.jpeg"


MessageDownloadable = MessageWithDocument | MessageWithCompressedPhoto


def is_downloadable(
    msg: Message,
) -> TypeGuard["MessageDownloadable"]:
    return MessageWithDocument.guard(msg) or MessageWithCompressedPhoto.guard(msg)


class MessageWithDocumentImage(Message):
    """message with uncompressed image"""

    file: File
    document: Document

    @staticmethod
    def guard(msg: Message) -> TypeGuard["MessageWithDocumentImage"]:
        return (
            msg.document is not None
            and get_attribute(msg.document, types.DocumentAttributeImageSize)
            is not None
            and not MessageWithSticker.guard(msg)
        )

    @staticmethod
    def filename(msg: "MessageWithDocumentImage"):
        return f"{msg.id}_{msg.file.name}"


class MessageWithZip(Message):
    """message with a zip file"""

    file: File
    document: Document

    @staticmethod
    def guard(msg: Message) -> TypeGuard["MessageWithZip"]:
        return (
            msg.document is not None
            and msg.file is not None
            and msg.file.name is not None
            and msg.file.name.endswith(".zip")
        )

    @staticmethod
    def filename(msg: "MessageWithZip"):
        return f"{msg.id}_{msg.file.name}"


class MessageWithVideo(Message):
    """circles, video documents, stickers, gifs"""

    file: File
    document: Document

    @staticmethod
    def guard(msg: Message) -> TypeGuard["MessageWithVideo"]:

        if msg.document is None:
            return False

        video = get_attribute(msg.document, types.DocumentAttributeVideo)

        return msg.document is not None and (
            video is not None or MessageWithVideoDocument.guard(msg)
        )

    @staticmethod
    def filename(msg: "MessageWithVideo"):
        return f"{msg.id}_video{msg.file.ext}"


class MessageWithSticker(Message):
    """stickers"""

    file: File
    document: Document

    @staticmethod
    def guard(msg: Message) -> TypeGuard["MessageWithSticker"]:
        return bool(msg.sticker)

    @staticmethod
    def filename(msg: "MessageWithSticker"):
        return f"{msg.id}_sticker_{msg.file.name}"


class MessageWithCircle(Message):
    """circles"""

    file: File
    document: Document

    @staticmethod
    def guard(msg: Message) -> TypeGuard["MessageWithCircle"]:

        if msg.document is None:
            return False

        video = get_attribute(msg.document, types.DocumentAttributeVideo)

        return (
            msg.document is not None
            and video is not None
            and video.round_message is True
        )

    @staticmethod
    def filename(msg: "MessageWithCircle"):
        return f"{msg.id}_circle{msg.file.ext}"


class MessageWithVideoCompressed(Message):
    """compressed video documents"""

    file: File
    document: Document

    @staticmethod
    def guard(msg: Message) -> TypeGuard["MessageWithVideoCompressed"]:
        return (
            MessageWithVideo.guard(msg)
            and not MessageWithCircle.guard(msg)
            and not MessageWithAnimated.guard(msg)
            # and not MessageWithVideoDocument.guard(msg)
        )


class MessageWithVideoDocument(Message):
    """uncompressed video documents"""

    file: File
    document: Document

    @staticmethod
    def guard(msg: Message) -> TypeGuard["MessageWithVideoDocument"]:
        return (
            MessageWithDocument.guard(msg)
            and msg.file is not None
            and msg.file.mime_type is not None
            and msg.file.mime_type.startswith("video")
        )


class MessageWithAnimated(Message):
    """stickers, gifs"""

    file: File
    document: Document

    @staticmethod
    def guard(msg: Message) -> TypeGuard["MessageWithAnimated"]:
        if msg.document is None:
            return False

        video = get_attribute(msg.document, types.DocumentAttributeVideo)
        animated = bool(get_attribute(msg.document, types.DocumentAttributeAnimated))

        return msg.document is not None and video is not None and animated is True


class MessageWithAudio(Message):
    """voices and music"""

    document: Document

    @staticmethod
    def guard(msg: Message) -> TypeGuard["MessageWithAudio"]:

        if msg.document is None:
            return False

        audio = get_attribute(
            msg.document,
            types.DocumentAttributeAudio,
        )

        return audio is not None


class MessageWithVoice(Message):
    file: File
    document: Document

    @staticmethod
    def guard(msg: Message) -> TypeGuard["MessageWithVoice"]:
        return bool(msg.voice)


class MessageWithMusic(MessageWithDocument):
    """message with document audio tacks (without voices)"""

    file: File
    document: Document

    @staticmethod
    def guard(msg: Message) -> TypeGuard["MessageWithMusic"]:

        if msg.document is None:
            return False

        audio = get_attribute(
            msg.document,
            types.DocumentAttributeAudio,
        )

        return (
            msg.file is not None
            and msg.file.name is not None
            and audio is not None
            and audio.voice is False
        )

    @staticmethod
    def filename(msg: "MessageWithMusic"):
        return f"{msg.id}_{msg.file.name}"

    @staticmethod
    def peformer(msg: "MessageWithMusic"):
        return msg.file.performer

    @staticmethod
    def title(msg: "MessageWithMusic"):
        return msg.file.title

    @staticmethod
    def group_by_performer(
        messages: Iterable["MessageWithMusic"],
        minimum=2,
    ) -> tuple[dict[str, list["MessageWithMusic"]], list["MessageWithMusic"]]:

        messages = list(messages)
        no_performer = [t for t in messages if t.file.performer is None]
        with_performer = [t for t in messages if t.file.performer is not None]

        tracks = func.group_by0(lambda t: t.file.performer.lower(), with_performer)

        result = []

        for perf, tracks in tracks.items():
            if len(tracks) < minimum:
                no_performer.extend(tracks)
            else:
                result.append((perf, tracks))

        return dict(result), no_performer


class MessageWithText(Message):
    message: str

    @staticmethod
    def guard(msg: Message) -> TypeGuard["MessageWithText"]:
        return isinstance(msg.message, str) and len(msg.message) > 0


class MessageWithOtherDocument(Message):
    """other documents with file name"""

    document: Document

    @staticmethod
    def guard(msg: Message) -> TypeGuard["MessageWithOtherDocument"]:

        if not MessageWithFilename.guard(msg):
            return False

        return msg.document is not None and not (
            MessageWithDocumentImage.guard(msg)
            or MessageWithCompressedPhoto.guard(msg)
            or MessageWithVideo.guard(msg)
            or MessageWithAudio.guard(msg)
            or MessageWithSticker.guard(msg)
            or MessageWithAnimated.guard(msg)
            or MessageWithVideoDocument.guard(msg)
        )


# class MessageWithMedia(Message):
#     media: MessageMedia

#     @staticmethod
#     def guard(msg: Message) -> TypeGuard["MessageWithMedia"]:
#         return msg.media is not None
