from abc import abstractclassmethod, abstractmethod, abstractstaticmethod
from telethon.tl.custom import Message
from typing import (
    Any,
    Awaitable,
    Callable,
    Iterable,
    Mapping,
    Optional,
    Protocol,
    Type,
    TypeGuard,
)
from dataclasses import dataclass, fields
from tgmount import tg_vfs, tgclient, vfs
from tgmount.cache import CacheFactory


class FilterAllMessagesProto(Protocol):
    @abstractmethod
    def __init__(self, **kwargs) -> None:
        pass

    @abstractmethod
    async def filter(self, messages: Iterable[Message]) -> list[Message]:
        ...

    @abstractstaticmethod
    def from_config(*args) -> "FilterAllMessagesProto":
        ...

    # @abstractclassmethod
    # def filter(cls, messages: Iterable[Message]) -> list[Message]:
    #     ...


FilterSingleMessage = Callable[[Message], TypeGuard[Any]]
FilterAllMessages = FilterAllMessagesProto

Filter = FilterAllMessages


DirWrapper = Callable[[vfs.DirContentProto], Awaitable[vfs.DirContentProto]]
DirWrapperConstructor = Callable[[..., Any], Awaitable[DirWrapper]]

MessagesWrapper = Callable[[Iterable[Message]], Awaitable[list[Message]]]


class TgmountError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


@dataclass
class CreateRootResources:
    file_factory: tg_vfs.FileFactory
    sources: Mapping[str, tgclient.TelegramMessageSource]
    filters: Mapping[str, Type[Filter]]
    caches: Mapping[str, tg_vfs.FileFactory]
    wrappers: Mapping[str, DirWrapper]


TgmountRoot = Callable[
    [CreateRootResources],
    Awaitable[vfs.DirContentSource],
]


class FilterProviderProto(Protocol):
    @abstractmethod
    def get_filters(self) -> Mapping[str, Filter]:
        pass


class DirWrapperProviderProto(Protocol):
    @abstractmethod
    def get_wrappers(self) -> Mapping[str, DirWrapper]:
        pass

    @abstractmethod
    async def get_wrappers_factory(self, wrapper_type: str) -> DirWrapperConstructor:
        pass


class CachesProviderProto(Protocol):
    @abstractmethod
    def get_caches(self) -> Mapping[str, Type[CacheFactory]]:
        pass

    @abstractmethod
    async def get_cache_factory(self, cache_type: str) -> Type[CacheFactory]:
        pass
