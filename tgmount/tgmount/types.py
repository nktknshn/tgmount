from abc import abstractmethod
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


Filter = Callable[[Message], TypeGuard[Any]]


DirWrapper = Callable[[vfs.DirContentProto], Awaitable[vfs.DirContentProto]]
DirWrapperConstructor = Callable[[..., Any], Awaitable[DirWrapper]]
MessagesWrapper = Callable[[Iterable[Message]], Awaitable[list[Message]]]


class TgmountError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


@dataclass
class CreateRootContext:
    file_factory: tg_vfs.FileFactory
    # file_factory_cached: tg_vfs.FileFactory
    sources: Mapping[str, tgclient.TelegramMessageSource]
    filters: Mapping[str, Filter]
    caches: Mapping[str, tg_vfs.FileFactory]
    wrappers: Mapping[str, DirWrapper]


TgmountRoot = Callable[
    [CreateRootContext],
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
