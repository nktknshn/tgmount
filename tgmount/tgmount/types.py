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
from dataclasses import dataclass, replace
from tgmount import tg_vfs, tgclient, vfs
from tgmount.cache import CacheFactory

from .producers import TreeProducer
from .wrappers import DirContentWrapper

from .filters import Filter

# DirWrapper = Callable[[vfs.DirContentProto], Awaitable[vfs.DirContentProto]]
# DirWrapperConstructor = Callable[[..., Any], Awaitable[DirWrapper]]

# MessagesWrapper = Callable[[Iterable[Message]], Awaitable[list[Message]]]


@dataclass
class CreateRootResources:
    file_factory: tg_vfs.FileFactoryProto
    sources: Mapping[str, tgclient.TelegramMessageSourceProto]
    filters: Mapping[str, Type[Filter]]
    producers: Mapping[str, Type[TreeProducer]]
    caches: Mapping[str, tg_vfs.FileFactoryProto]
    wrappers: Mapping[str, Type[DirContentWrapper]]
    classifier: tg_vfs.ClassifierBase


TgmountRoot = Callable[
    [CreateRootResources],
    Awaitable[vfs.DirContentSource],
]
