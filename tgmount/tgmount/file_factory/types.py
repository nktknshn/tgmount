from abc import abstractmethod
from typing import Iterable, Mapping, Optional, Protocol, TypeGuard, TypeVar

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
    async def filename(
        self, message: T, *, factory_props: Mapping | None = None
    ) -> str:
        ...

    @abstractmethod
    async def file_content(
        self, message: T, *, factory_props: Mapping | None = None
    ) -> vfs.FileContent:
        ...

    @abstractmethod
    async def file(
        self, message: T, name=None, *, factory_props: Mapping | None = None
    ) -> vfs.FileLike:
        ...

    @abstractmethod
    def try_get(
        self, message: Message, *, factory_props: Mapping | None = None
    ) -> Optional[T]:
        ...

    @abstractmethod
    async def size(self, message: Message) -> int:
        ...

    @measure_time_sync(logger_func=print)
    def filter_supported(
        self, messages: Iterable[T], *, factory_props: Mapping | None = None
    ):
        msgs = [self.try_get(m, factory_props=factory_props) for m in messages]

        return list(filter(is_not_none, msgs))
