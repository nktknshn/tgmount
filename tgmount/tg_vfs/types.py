from abc import abstractmethod
from typing import Optional, Protocol, TypeGuard, TypeVar

from tgmount import vfs
from tgmount.tgclient import guards
from telethon.tl.custom import Message


T = TypeVar("T")


class FileContentProto(Protocol):
    @abstractmethod
    def file_content(self, message: guards.MessageDownloadable) -> vfs.FileContent:
        ...


class FileFactoryProto(Protocol[T]):
    @abstractmethod
    def supports(self, message: Message) -> TypeGuard[T]:
        ...

    @abstractmethod
    def filename(
        self,
        message: T,
    ) -> str:
        ...

    @abstractmethod
    def file(self, message: T, name: Optional[str]) -> vfs.FileLike:
        ...
