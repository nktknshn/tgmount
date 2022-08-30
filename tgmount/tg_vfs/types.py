from abc import abstractmethod
from typing import Optional, Protocol, TypeGuard, TypeVar

from tgmount import vfs
from tgmount.tg_vfs.tree.types import MessagesTree
from tgmount.tgclient import guards
from telethon.tl.custom import Message

T = TypeVar("T")


class DirContentSourceCreatorProto:
    @abstractmethod
    def create_dir_content_source(
        self: "FileFactoryProto",
        tree: MessagesTree[Message],
    ) -> vfs.DirContentSource:
        ...


class SupportsMethodProto(Protocol[T]):
    @abstractmethod
    def supports(self, message: Message) -> TypeGuard[T]:
        ...


class FileContentProviderProto(Protocol[T]):
    @abstractmethod
    def file_content(self, message: guards.MessageDownloadable) -> vfs.FileContent:
        ...


class WithFileContentMethodProto(Protocol[T]):
    @classmethod
    @abstractmethod
    def file_content(cls, file_factory: "FileFactoryProto") -> vfs.FileContentProto:
        ...

    @staticmethod
    def guard(klass) -> TypeGuard["WithFileContentMethodProto"]:
        return hasattr(klass, "file_content")


class WithFilenameMethodProto(Protocol[T]):
    @abstractmethod
    def filename(self, message: T) -> str:
        ...


class FileFactoryProto(Protocol[T]):
    @abstractmethod
    def supports(self, message: Message) -> TypeGuard[T]:
        ...

    @abstractmethod
    def filename(self, message: T) -> str:
        ...

    @abstractmethod
    def file_content(self, message: T) -> vfs.FileContent:
        ...

    @abstractmethod
    def file(self, message: T, name=None) -> vfs.FileLike:
        ...

    @abstractmethod
    def try_get(
        self, message: Message, treat_as: Optional[list[str]] = None
    ) -> Optional[T]:
        ...

    @abstractmethod
    def size(self, message: Message) -> int:
        ...
