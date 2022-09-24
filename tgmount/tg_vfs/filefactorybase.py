from abc import abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, ClassVar, Protocol, TypeGuard, TypeVar

from telethon.tl.custom import Message
from tgmount import vfs
from tgmount.tg_vfs.classifier import ClassifierBase
from tgmount.tg_vfs.error import FileFactoryError
from tgmount.tgclient.guards import *
from tgmount.util import is_not_none, none_fallback

from .error import FileFactoryError

from .types import (
    FileContentProviderProto,
    FileFactoryProto,
)


T = TypeVar("T")
C = TypeVar("C", bound=WithTryGetMethodProto)


TryGetFunc = Callable[[Message], Optional[T]]

SupportedClass = WithTryGetMethodProto[T]
FilenameGetter = Callable[[T], str]
FileContentGetter = Callable[[T], vfs.FileContentProto]
FileGetter = Callable[[T, Optional[str]], vfs.FileLike]


@dataclass
class FileFactoryItem:
    klass: Type[WithTryGetMethodProto]
    filename: FilenameGetter
    content: Optional[FileContentGetter]
    file: Optional[FileGetter]


ClassName = str

import functools


class FileFactoryBase(FileFactoryProto[T]):
    def __init__(self) -> None:
        self._supported: dict[ClassName, FileFactoryItem] = {}

        self._cache: dict[Message, Optional[Type[T]]] = {}

    def register(
        self,
        klass: Type[C],
        filename: FilenameGetter[C],
        file_content: Optional[FileContentGetter[C]] = None,
        file_getter: Optional[FileGetter[C]] = None,
    ):
        class_name = klass.__name__
        self._supported[class_name] = FileFactoryItem(
            klass=klass,
            filename=filename,
            content=file_content,
            file=file_getter,
        )

    @property
    def supported(self) -> list[Type[SupportedClass]]:
        return list(map(lambda item: item.klass, self._supported.values()))

    def supports(self, input_item: Any) -> bool:
        return self.try_get(input_item) is not None

    def get_supported(self, input_items: list[Any]) -> list[T]:
        return list(filter(is_not_none, map(self.try_get, input_items)))

    def try_get(
        self, input_item: Any, treat_as: Optional[list[str]] = None
    ) -> Optional[T]:
        # if input_item in self._cache:
        # return self._cache[input_item]

        if (klass := self.try_get_cls(input_item, treat_as)) is not None:
            msg = klass.try_get(input_item)
            # self._cache[input_item] = msg

            return msg

        # self._cache[input_item] = None
        return None

    def try_get_cls(
        self, input_item: Any, treat_as: Optional[list[str]] = None
    ) -> Optional[Type[T]]:
        treat_as = none_fallback(treat_as, [])

        for cls_name in treat_as:
            if (klass := self._supported.get(cls_name)) is not None:
                if (m := klass.klass.try_get(input_item)) is not None:
                    return klass.klass

        for klass in self.supported:
            if (m := klass.try_get(input_item)) is not None:
                return klass

        return None

    def get_cls(
        self, supported_item: T, treat_as: Optional[list[str]] = None
    ) -> Type[T]:

        klass = self.try_get_cls(supported_item, treat_as)

        if klass is None:
            raise FileFactoryError(f"{supported_item} is not supported.")

        return klass

    def get_cls_item(
        self, supported_item: T, *, treat_as: Optional[list[str]] = None
    ) -> FileFactoryItem:
        class_name = self.get_cls(supported_item, treat_as).__name__
        return self._supported[class_name]

    def size(
        self,
        supported_item: T,
        *,
        treat_as: Optional[list[str]] = None,
    ) -> int:
        return self.file_content(supported_item, treat_as=treat_as).size

    def filename(
        self,
        supported_item: T,
        *,
        treat_as: Optional[list[str]] = None,
    ) -> str:
        return self.get_cls_item(supported_item, treat_as=treat_as).filename(
            supported_item
        )

    @abstractmethod
    def file(
        self,
        supported_item: T,
        name=None,
        *,
        treat_as: Optional[list[str]] = None,
    ) -> vfs.FileLike:
        ...

    @abstractmethod
    def file_content(
        self,
        supported_item: T,
        *,
        treat_as: Optional[list[str]] = None,
    ) -> vfs.FileContent:
        ...


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


class FileFactoryDefault(
    FileFactoryBase[FileFactorySupportedTypes],
):
    def __init__(
        self,
        files_source: FileContentProviderProto,
        extra_files_source: Mapping[str, FileContentProviderProto] | None = None,
    ) -> None:
        super().__init__()
        self._files_source = files_source
        self.register_classes()

    @property
    def try_get_dict(self) -> Mapping[str, Type[TryGetFunc]]:
        return {f.__name__: f.try_get for f in self.supported}

    def message_type(self, item: FileFactorySupportedTypes):
        return self.get_cls(item)

    def message_types(self, item: FileFactorySupportedTypes):
        return [self.get_cls(item)]

    def register_classes(self):

        self.register(
            klass=MessageWithCompressedPhoto,
            filename=MessageWithCompressedPhoto.filename,
        )
        self.register(klass=MessageWithMusic, filename=MessageWithMusic.filename)
        self.register(klass=MessageWithVoice, filename=MessageWithVoice.filename)
        self.register(klass=MessageWithSticker, filename=MessageWithSticker.filename)
        self.register(klass=MessageWithAnimated, filename=MessageWithAnimated.filename)
        self.register(
            klass=MessageWithKruzhochek, filename=MessageWithKruzhochek.filename
        )
        self.register(
            klass=MessageWithDocumentImage, filename=MessageWithDocumentImage.filename
        )
        self.register(
            klass=MessageWithVideoFile, filename=MessageWithVideoFile.filename
        )
        self.register(klass=MessageWithVideo, filename=MessageWithVideo.filename)
        self.register(
            klass=MessageWithOtherDocument, filename=MessageWithOtherDocument.filename
        )
        self.register(klass=MessageWithFilename, filename=MessageWithFilename.filename)
        self.register(klass=MessageDownloadable, filename=MessageDownloadable.filename)

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
