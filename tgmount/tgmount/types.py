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
    TypeVar,
)
from dataclasses import dataclass, replace
from tgmount import tg_vfs, tgclient, vfs
from tgmount.tgmount.vfs_wrappers import VfsWrapperProto

from .wrappers import DirContentWrapper

from .filters import Filter, FiltersMapping
from .vfs_structure_producers_provider import VfsProducersProviderProto
from .provider_sources import SourcesProviderProto


@dataclass
class CreateRootResources:
    file_factory: tg_vfs.FileFactoryProto
    sources: SourcesProviderProto
    filters: FiltersMapping
    producers: VfsProducersProviderProto
    caches: Mapping[str, tg_vfs.FileFactoryProto]
    wrappers: Mapping[str, Type[DirContentWrapper]]
    vfs_wrappers: Mapping[str, Type[VfsWrapperProto]]
    classifier: tg_vfs.ClassifierBase

    def set_sources(self, sources: SourcesProviderProto):
        return replace(self, sources=sources)


TgmountRoot = Callable[
    [CreateRootResources],
    Awaitable[vfs.DirContentSource],
]
