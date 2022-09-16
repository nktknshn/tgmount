from collections.abc import Awaitable, Callable, Mapping
from typing import Iterable, Optional, Protocol, TypeVar

import telethon
from telethon.tl.custom import Message

from tgmount import fs, tglog, vfs
from tgmount.tg_vfs.tree.helpers.remove_empty import (
    filter_empty,
    remove_empty_dirs_content,
)
from tgmount.tgclient.message_source import Subscribable
from tgmount.tgmount.util import sets_difference
from tgmount.tgmount.vfs_structure_producer import (
    VfsStructureFromConfigProducerVfsStructe,
)
from tgmount.tgmount.vfs_wrappers import VfsWrapperProto
from tgmount.util import none_fallback

from .tgmount_root_producer_types import Set
from .vfs_structure_types import (
    PutEntity,
    VfsStructureProducerProto,
    VfsStructureBaseProto,
    VfsStructureProto,
)
from .vfs_structure import VfsStructure
from .wrappers import DirContentWrapper, ExcludeEmptyDirs
from dataclasses import replace

import tgmount.tglog as log

logger = log.getLogger("ExcludeEmptyWrappr")


class ExcludeEmptyWrapprStructure(VfsStructureProto):
    def __init__(self, state: dict, vfs_structure: VfsStructureProto) -> None:
        self._vfs_structure = vfs_structure
        self._state = state

    async def get_difference(self):
        last_dirs = self._state.get("last_dirs", Set())
        self._state["last_dirs"] = last_dirs

        s, c = await self.list_content()

        current_dirs = Set(s.keys()) | Set(
            item.name for item in c if isinstance(c, vfs.DirLike)
        )

        self._state["last_dirs"] = current_dirs

        if len(last_dirs) == 0:
            return Set(), Set()
        else:
            removed, new, common = sets_difference(last_dirs, current_dirs)
            return removed, new

    async def list_content(
        self,
    ) -> tuple[dict[str, "VfsStructureProto"], list[vfs.DirContentItem]]:
        subdirs = {}

        _subdirs, _content = await self._vfs_structure.list_content()

        for name, vs in _subdirs.items():
            _s, _c = await vs.list_content()

            if len(_s) > 0 or len(_c) > 0:
                subdirs[name] = vs

        # for c in _content:
        #     if isinstance(c, vfs.DirLike):
        #         content.append(c)
        #     else:
        #         content.append(c)

        return subdirs, _content


class ExcludeEmptyWrappr(VfsWrapperProto):
    def __init__(self, **kwargs) -> None:
        pass

    async def wrap_vfs_structure(self, state: dict, struct) -> VfsStructureProto:
        return ExcludeEmptyWrapprStructure(state, struct)

    async def wrap_update(
        self,
        state: dict,
        vfs_structure: VfsStructureFromConfigProducerVfsStructe,
        update: fs.FileSystemOperationsUpdate,
    ) -> fs.FileSystemOperationsUpdate:

        logger.info(f"wrap_update({update})")

        content = await vfs_structure.get_dir_content_list()

        dir_content = vfs.dir_content(*content)
        update.update_dir_content.append("/")
        # update.update_dir_content["/"] = dir_content

        return update

    @staticmethod
    def from_config(cfg: dict):
        return ExcludeEmptyWrappr()


class ExcludeEmptyProducer(VfsStructureProducerProto):
    def __init__(self, *args) -> None:
        super().__init__(*args)

    async def produce_vfs_struct(self) -> VfsStructureProto:
        ...

    async def get_vfs_structure(self) -> VfsStructureProto:
        return super().get_vfs_structure()

    @staticmethod
    def from_config(root_producer, resources):
        pass
