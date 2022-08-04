from datetime import datetime
from typing import Any, Awaitable, Callable, Optional, Protocol, overload

import telethon
from tgmount import vfs
from tgmount.tgclient import Document, Message
from tgmount.tgclient.search.filtering.guards import (
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


class FileFunc:
    # @overload
    # def file(
    #     self: FileContentProvider,
    #     message: MessageWithDocument,
    # ) -> vfs.FileLike:
    #     ...

    # @overload
    # def file(
    #     self: FileContentProvider,
    #     message: MessageWithPhoto,
    # ) -> vfs.FileLike:
    #     ...

    # @overload
    # def file(
    #     self: FileContentProvider,
    #     message: MessageWithDocumentImage,
    # ) -> vfs.FileLike:
    #     ...

    # @overload
    # def file(
    #     self: FileContentProvider,
    #     message: MessageWithVideo,
    # ) -> vfs.FileLike:
    #     ...

    def file(
        self: FileContentProvider,
        message: MessageWithCompressedPhoto
        | MessageWithVideo
        | MessageWithDocument
        | MessageWithFilename
        | MessageWithDocumentImage
        | MessageWithVoice
        | MessageWithCircle
        | MessageWithZip
        | MessageWithMusic
        | MessageWithOtherDocument,
    ) -> vfs.FileLike:

        creation_time = getattr(message, "date", datetime.now())

        if MessageWithCompressedPhoto.guard(message):
            return vfs.FileLike(
                f"{message.id}_photo.jpeg",
                content=self.file_content(message, message.photo),
                creation_time=creation_time,
            )
        elif MessageWithVoice.guard(message):
            return vfs.FileLike(
                f"{message.id}_voice{message.file.ext}",
                content=self.file_content(message, message.document),
                creation_time=creation_time,
            )
        elif MessageWithSticker.guard(message):
            return vfs.FileLike(
                f"{message.id}_sticker_{message.file.name}",
                content=self.file_content(message, message.document),
                creation_time=creation_time,
            )
        elif MessageWithAnimated.guard(message):
            return vfs.FileLike(
                f"{message.id}_gif{message.file.ext}",
                content=self.file_content(message, message.document),
                creation_time=creation_time,
            )
        elif MessageWithCircle.guard(message):
            return vfs.FileLike(
                f"{message.id}_circle{message.file.ext}",
                content=self.file_content(message, message.document),
                creation_time=creation_time,
            )
        elif MessageWithFilename.guard(message):
            return vfs.FileLike(
                f"{message.id}_{message.file.name}",
                content=self.file_content(message, message.document),
                creation_time=creation_time,
            )
        elif MessageWithVideo.guard(message):
            return vfs.FileLike(
                f"{message.id}_video{message.file.ext}",
                content=self.file_content(message, message.document),
                creation_time=creation_time,
            )
        elif MessageWithMusic.guard(message):
            return vfs.FileLike(
                f"{message.id}_{message.file.name}",
                content=self.file_content(message, message.document),
                creation_time=creation_time,
            )
        raise ValueError(f"incorret input message: {message_to_str(message)}")


class ContentFunc:
    @overload
    def content(
        self: FileContentProvider,
        message: MessageWithDocument,
    ) -> vfs.FileContent:
        ...

    @overload
    def content(
        self: FileContentProvider,
        message: MessageWithCompressedPhoto,
    ) -> vfs.FileContent:
        ...

    @overload
    def content(
        self: FileContentProvider,
        message: MessageWithVideo,
    ) -> vfs.FileContent:
        ...

    @overload
    def content(
        self: FileContentProvider,
        message: MessageWithMusic,
    ) -> vfs.FileContent:
        ...

    def content(
        self: FileContentProvider,
        message: MessageWithCompressedPhoto
        | MessageWithDocument
        | MessageWithVideo
        | MessageWithMusic,
    ) -> vfs.FileContent:
        if MessageWithCompressedPhoto.guard(message):
            return self.file_content(message, message.photo)
        elif MessageWithDocument.guard(message):
            return self.file_content(message, message.document)

        raise ValueError("incorret input message")
