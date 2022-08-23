from abc import abstractmethod
from typing import Optional, Protocol, TypeGuard, TypeVar

from tgmount import vfs
from tgmount.tgclient import guards
from telethon.tl.custom import Message


T = TypeVar("T")


class SupportsMethodProto(Protocol[T]):
    @abstractmethod
    def supports(self, message: Message) -> TypeGuard[T]:
        ...


class FileContentProto(Protocol[T]):
    @abstractmethod
    def file_content(self, message: T) -> vfs.FileContent:
        ...


class FilenameMethodProto(Protocol[T]):
    @abstractmethod
    def filename(self, message: T) -> str:
        ...


class FileFactoryProto(Protocol[T]):
    @abstractmethod
    def supports(self, message: Message) -> TypeGuard[T]:
        pass

    @abstractmethod
    def filename(self, message: T) -> str:
        ...

    @abstractmethod
    def file_content(self, message: guards.MessageDownloadable) -> vfs.FileContent:
        ...

    @abstractmethod
    def file(self, message: T, name=None) -> vfs.FileLike:
        ...
