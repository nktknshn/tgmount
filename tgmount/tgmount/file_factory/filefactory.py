from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Generic, Mapping, Type

from tgmount import vfs
from tgmount.tgclient.guards import *
from tgmount.util import none_fallback
from .types import (
    FileContentProviderProto,
)
from .filefactorybase import FileFactoryBase, TryGetFunc

FileFactorySupportedTypes = (
    MessageWithMusic
    | MessageWithVoice
    | MessageWithSticker
    | MessageWithAnimated
    | MessageWithKruzhochek
    | MessageWithCompressedPhoto
    | MessageWithDocumentImage
    | MessageWithVideoFile
    | MessageWithVideo
    | MessageWithOtherDocument
    | MessageWithFilename
    | MessageDownloadable
)


class FileFactoryDefault(FileFactoryBase[FileFactorySupportedTypes | T], Generic[T]):
    """Takes a telegram message and produces vfs.FileLike or vfs.FileContentProto"""

    def __init__(
        self,
        files_source: FileContentProviderProto,
        # extra_files_source: Mapping[str, FileContentProviderProto] | None = None,
    ) -> None:
        super().__init__()
        self._files_source = files_source

    def file_content(
        self, supported_item: FileFactorySupportedTypes, treat_as=None
    ) -> vfs.FileContentProto:

        if (
            cf := self.get_cls_item(supported_item, treat_as=treat_as).content
        ) is not None:
            return cf(supported_item)

        return self._files_source.file_content(supported_item)

    def file(
        self, supported_item: FileFactorySupportedTypes, name=None, treat_as=None
    ) -> vfs.FileLike:

        creation_time = getattr(supported_item, "date", datetime.now())

        doc_id = (
            MessageDownloadable.document_or_photo_id(supported_item)
            if MessageDownloadable.guard(supported_item)
            else None
        )
        message_id = (
            supported_item.id if TelegramMessage.guard(supported_item) else None
        )

        extra = (message_id, doc_id)

        return vfs.FileLike(
            name=none_fallback(name, self.filename(supported_item, treat_as=treat_as)),
            content=self.file_content(supported_item, treat_as=treat_as),
            extra=extra,
            creation_time=creation_time,
        )


FileFactoryDefault.register(
    klass=MessageWithCompressedPhoto,
    filename=MessageWithCompressedPhoto.filename,
)
FileFactoryDefault.register(klass=MessageWithMusic, filename=MessageWithMusic.filename)
FileFactoryDefault.register(klass=MessageWithVoice, filename=MessageWithVoice.filename)
FileFactoryDefault.register(
    klass=MessageWithSticker, filename=MessageWithSticker.filename
)
FileFactoryDefault.register(
    klass=MessageWithAnimated, filename=MessageWithAnimated.filename
)
FileFactoryDefault.register(
    klass=MessageWithKruzhochek, filename=MessageWithKruzhochek.filename
)
FileFactoryDefault.register(
    klass=MessageWithDocumentImage, filename=MessageWithDocumentImage.filename
)
FileFactoryDefault.register(
    klass=MessageWithVideoFile, filename=MessageWithVideoFile.filename
)
FileFactoryDefault.register(klass=MessageWithVideo, filename=MessageWithVideo.filename)
FileFactoryDefault.register(
    klass=MessageWithOtherDocument, filename=MessageWithOtherDocument.filename
)
FileFactoryDefault.register(
    klass=MessageWithFilename, filename=MessageWithFilename.filename
)
FileFactoryDefault.register(
    klass=MessageDownloadable, filename=MessageDownloadable.filename
)
