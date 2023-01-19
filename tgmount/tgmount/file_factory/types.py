from abc import abstractmethod
from typing import Iterable, Optional, Protocol, TypeGuard, TypeVar

from telethon.tl.custom import Message

from tgmount import vfs
from tgmount.fs.util import measure_time_sync
from tgmount.tgclient import guards
from tgmount.util import is_not_none

T = TypeVar("T")


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
    """Constructs a `FileLike` from a message of type `T`"""

    @abstractmethod
    def supports(self, message: Message) -> TypeGuard[T]:
        ...

    @abstractmethod
    def filename(self, message: T, *, treat_as: list[str] | None = None) -> str:
        ...

    @abstractmethod
    def file_content(
        self, message: T, *, treat_as: list[str] | None = None
    ) -> vfs.FileContent:
        ...

    @abstractmethod
    def file(
        self, message: T, name=None, *, treat_as: list[str] | None = None
    ) -> vfs.FileLike:
        ...

    @abstractmethod
    def try_get(
        self, message: Message, *, treat_as: Optional[list[str]] = None
    ) -> Optional[T]:
        ...

    @abstractmethod
    def size(self, message: Message) -> int:
        ...

    @measure_time_sync(logger_func=print)
    def filter_supported(
        self, messages: Iterable[T], *, treat_as: Optional[list[str]] = None
    ):
        msgs = [self.try_get(m, treat_as=treat_as) for m in messages]

        return list(filter(is_not_none, msgs))
