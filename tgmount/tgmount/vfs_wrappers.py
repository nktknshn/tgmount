from abc import abstractmethod, abstractstaticmethod
from collections.abc import Awaitable, Callable, Mapping
from typing import Iterable, Optional, Protocol, TypeVar

import telethon
from telethon.tl.custom import Message

from tgmount import fs, tglog, vfs

from .vfs_structure_types import VfsStructureProducerProto, VfsStructureProto


class VfsWrapperProto(Protocol):
    @abstractmethod
    def __init__(self, **kwargs) -> None:
        pass

    @abstractmethod
    async def wrap_vfs_structure(
        self, state: dict, vfs_structure: VfsStructureProto
    ) -> VfsStructureProto:
        ...

    @abstractmethod
    async def wrap_update(
        self,
        state: dict,
        structure: VfsStructureProto,
        update: fs.FileSystemOperationsUpdate,
    ) -> fs.FileSystemOperationsUpdate:
        ...

    @abstractstaticmethod
    def from_config(*args) -> "VfsWrapperProto":
        ...
