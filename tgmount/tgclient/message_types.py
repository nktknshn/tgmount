from abc import abstractmethod
from typing import Any, Optional, Protocol

import telethon

MessageId = int
ChatId = int


class StickerProto(Protocol):
    pass


class VideoProto(Protocol):
    pass


class VideoNoteProto(Protocol):
    pass


class GifProto(Protocol):
    pass


class AudioProto(Protocol):
    pass


class VoiceProto(Protocol):
    pass


class ReactionsProto(Protocol):
    pass


class SenderProto(Protocol):
    username: str | None


class ForwardProto(Protocol):
    from_name: str | None
    from_id: int
    is_channel: bool
    is_group: bool

    @abstractmethod
    async def get_chat():
        ...


class FileProto(Protocol):
    name: str | None
    mime_type: str | None
    ext: str | None
    performer: str | None
    title: str | None
    duration: int | None


class DocumentProto(Protocol):
    id: int
    size: int
    access_hash: int
    file_reference: bytes
    attributes: list

    @staticmethod
    def guard_document_image(document: "DocumentProto"):
        return (
            DocumentProto.get_attribute(
                document, telethon.types.DocumentAttributeImageSize
            )
            is not None
        )

    @staticmethod
    def get_attribute(doc: "DocumentProto", attr_cls) -> Optional[Any]:
        for attr in doc.attributes:
            if isinstance(attr, attr_cls):
                return attr


class PhotoSizeProto:
    type: str
    w: int
    h: int
    size: int


class PhotoProto(Protocol):
    id: int
    access_hash: int
    file_reference: bytes
    sizes: list[PhotoSizeProto | Any]

    @staticmethod
    def guard(photo: Any):
        return isinstance(photo, telethon.types.Photo)


class MessageProto(Protocol):
    id: MessageId
    chat_id: ChatId
    text: str | None
    file: FileProto | None
    document: DocumentProto | None
    forward: ForwardProto | None
    photo: PhotoProto | None
    sticker: StickerProto | None
    video_note: VideoNoteProto | None
    video: VideoProto | None
    gif: GifProto | None
    audio: AudioProto | None
    voice: VoiceProto | None
    reactions: ReactionsProto | None

    @abstractmethod
    async def get_sender() -> SenderProto:
        ...

    @staticmethod
    def guard(msg: Any):
        return (
            hasattr(msg, "id")
            and hasattr(msg, "document")
            and hasattr(msg, "file")
            and hasattr(msg, "forward")
            # and hasattr(msg, "media")
        )
