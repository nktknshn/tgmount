from abc import abstractmethod
from telethon.tl.custom import Message
from typing import Any, Awaitable, Callable, Mapping, Optional, Protocol, TypeGuard
from dataclasses import dataclass, fields
from tgmount import tg_vfs, tgclient, vfs

Filter = Callable[[Message], TypeGuard[Any]]


class TgmountError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


@dataclass
class CreateRootContext:
    file_factory: tg_vfs.FileFactory
    # file_factory_cached: tg_vfs.FileFactory
    sources: Mapping[str, tgclient.TelegramMessageSource]
    filters: Mapping[str, Filter]


TgmountRoot = Callable[
    [CreateRootContext],
    Awaitable[vfs.DirContentSource],
]


class FilterProviderProto(Protocol):
    @abstractmethod
    def get_filters(self) -> Mapping[str, Filter]:
        pass
