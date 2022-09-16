from abc import abstractmethod, abstractstaticmethod
from typing import Awaitable, Callable, Iterable, Mapping, Protocol, TypeVar
from tgmount import tg_vfs, vfs
from telethon.tl.custom import Message
from tgmount.tgclient.guards import *

from .vfs_structure_types import VfsStructureProducerProto


T = TypeVar("T")


class VfsProducersProviderProto(Protocol):
    @property
    @abstractmethod
    def default(self) -> Type[VfsStructureProducerProto]:
        ...

    @abstractmethod
    def get_producers(self) -> Mapping[str, Type[VfsStructureProducerProto]]:
        pass


# class VfsProducersProviderBase(Protocol):
#     @property
#     @abstractmethod
#     def default(self) -> Type[VfsStructureProducerProto]:
#         ...

#     @abstractmethod
#     def get_producers(self) -> Mapping[str, Type[VfsStructureProducerProto]]:
#         pass
