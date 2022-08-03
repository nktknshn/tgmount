from datetime import datetime
from typing import Any, Awaitable, Callable, Optional, Protocol, overload

import telethon
from tgmount import vfs
from tgmount.tgclient import Document, Message
from tgmount.tgclient.search.filtering.guards import (
    MessageWithDocument,
    MessageWithDocumentImage,
    MessageWithFilename,
    MessageWithMusic,
    MessageWithPhoto,
    MessageWithVideo,
)

from .types import InputSourceItem


class FileContentProvider(Protocol):
    def file_content(
        self, message: Message, input_item: InputSourceItem
    ) -> vfs.FileContent:
        ...


class FileFunc:
    @overload
    def file(
        self: FileContentProvider,
        message: MessageWithDocument,
    ) -> vfs.FileLike:
        ...

    @overload
    def file(
        self: FileContentProvider,
        message: MessageWithPhoto,
    ) -> vfs.FileLike:
        ...

    @overload
    def file(
        self: FileContentProvider,
        message: MessageWithDocumentImage,
    ) -> vfs.FileLike:
        ...

    @overload
    def file(
        self: FileContentProvider,
        message: MessageWithVideo,
    ) -> vfs.FileLike:
        ...

    def file(
        self: FileContentProvider,
        message: MessageWithPhoto | MessageWithVideo | MessageWithDocument,
    ) -> vfs.FileLike:

        creation_time = getattr(message, "date", datetime.now())
        # int(message.date.timestamp() * 1e9) if message.date else time.time_ns()

        if MessageWithPhoto.guard(message):
            return vfs.FileLike(
                f"{message.id}_photo.jpeg",
                content=self.file_content(message, message.photo),
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
        elif MessageWithFilename.guard(message):
            return vfs.FileLike(
                f"{message.id}{message.file.name}",
                content=self.file_content(message, message.document),
                creation_time=creation_time,
            )

        raise ValueError("incorret input message")


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
        message: MessageWithPhoto,
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
        message: MessageWithPhoto
        | MessageWithDocument
        | MessageWithVideo
        | MessageWithMusic,
    ) -> vfs.FileContent:
        if MessageWithPhoto.guard(message):
            return self.file_content(message, message.photo)
        elif MessageWithDocument.guard(message):
            return self.file_content(message, message.document)

        raise ValueError("incorret input message")
