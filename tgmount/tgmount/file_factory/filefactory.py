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
from .filefactorybase import FileFactoryBase, TryGetFunc, resolve_future_or_value

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
    | T
)


class FileFactoryDefault(FileFactoryBase[FileFactorySupportedTypes | T], Generic[T]):
    """Takes a telegram message and produces vfs.FileLike or vfs.FileContentProto"""

    def __init__(
        self,
        files_source: FileContentProviderProto,
        factory_props: Mapping | None = None
        # extra_files_source: Mapping[str, FileContentProviderProto] | None = None,
    ) -> None:
        super().__init__(factory_props=factory_props)

        self._files_source = files_source
        self._supported = {**self._supported}

    async def file_content(
        self, supported_item: FileFactorySupportedTypes, factory_props=None
    ) -> vfs.FileContentProto:

        if (
            get_file_content := self.get_cls_item(
                supported_item, factory_props=factory_props
            ).content
        ) is not None:
            return await resolve_future_or_value(get_file_content(supported_item))

        return self._files_source.file_content(supported_item)

    async def file(
        self, supported_item: FileFactorySupportedTypes, name=None, factory_props=None
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
            name=none_fallback(
                name,
                await resolve_future_or_value(
                    self.filename(supported_item, factory_props=factory_props)
                ),
            ),
            content=await resolve_future_or_value(
                self.file_content(supported_item, factory_props=factory_props)
            ),
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
