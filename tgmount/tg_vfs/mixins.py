from datetime import datetime
from typing import (
    Any,
    Awaitable,
    Callable,
    Generic,
    Optional,
    Protocol,
    TypeGuard,
    TypeVar,
    overload,
)

import telethon
from tgmount import vfs
from tgmount.tgclient import Document, Message
from tgmount.tgclient.search.filtering.guards import (
    MessageDownloadable,
    MessageWithAnimated,
    MessageWithCircle,
    MessageWithDocument,
    MessageWithDocumentImage,
    MessageWithFilename,
    MessageWithMusic,
    MessageWithOtherDocument,
    MessageWithCompressedPhoto,
    MessageWithSticker,
    MessageWithVideo,
    MessageWithVoice,
    MessageWithZip,
)

from .types import InputSourceItem


class FileContentProvider(Protocol):
    def file_content(
        self, message: Message, input_item: InputSourceItem
    ) -> vfs.FileContent:
        ...


def message_to_str(m: Message):
    return f"Message(id={m.id}, file={m.file}, media={m.media}, document={m.document})"


T = TypeVar("T")


class FileFuncProto(Protocol, Generic[T]):
    def file(self, message: T) -> vfs.FileLike:
        ...

    def supports(self, message: Message) -> TypeGuard[T]:
        ...


FileFuncSupported = (
    MessageWithCompressedPhoto
    | MessageWithVideo
    | MessageWithDocument
    | MessageWithFilename
    | MessageWithDocumentImage
    | MessageWithVoice
    | MessageWithCircle
    | MessageWithZip
    | MessageWithMusic
    | MessageWithOtherDocument
)


class ContentFunc(Protocol):
    def content(
        self: FileContentProvider,
        message: MessageDownloadable,
    ) -> vfs.FileContent:
        if MessageWithCompressedPhoto.guard(message):
            return self.file_content(message, message.photo)
        elif MessageWithDocument.guard(message):
            return self.file_content(message, message.document)

        raise ValueError("incorret input message")


class FileFunc(
    FileFuncProto[FileFuncSupported],
    ContentFunc,
    FileContentProvider,
    Protocol,
):
    def supports(self, message: Message) -> TypeGuard[FileFuncSupported]:
        return any(
            map(
                lambda f: f(message),
                [
                    MessageWithCompressedPhoto.guard,
                    MessageWithVideo.guard,
                    MessageWithFilename.guard,
                    MessageWithDocumentImage.guard,
                    MessageWithVoice.guard,
                    MessageWithCircle.guard,
                    MessageWithZip.guard,
                    MessageWithMusic.guard,
                    MessageWithDocument.guard,
                    MessageWithOtherDocument.guard,
                ],
            )
        )

    def filename(
        self,
        message: FileFuncSupported,
    ) -> str:
        if MessageWithCompressedPhoto.guard(message):
            return MessageWithCompressedPhoto.filename(message)
        elif MessageWithVoice.guard(message):
            return f"{message.id}_voice{message.file.ext}"
        elif MessageWithSticker.guard(message):
            return MessageWithSticker.filename(message)
        elif MessageWithAnimated.guard(message):
            return f"{message.id}_gif{message.file.ext}"
        elif MessageWithCircle.guard(message):
            return f"{message.id}_circle{message.file.ext}"
        elif MessageWithVideo.guard(message):
            return f"{message.id}_video{message.file.ext}"
        elif MessageWithMusic.guard(message):
            return f"{message.id}_{message.file.name}"
        elif MessageWithFilename.guard(message):
            return f"{message.id}_{message.file.name}"

        raise ValueError(f"incorret input message: {message_to_str(message)}")

    def file(
        self,
        message: FileFuncSupported,
    ) -> vfs.FileLike:

        creation_time = getattr(message, "date", datetime.now())

        return vfs.FileLike(
            self.filename(message),
            content=self.content(message),
            creation_time=creation_time,
        )
