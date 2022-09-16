import os
from abc import abstractmethod, abstractstaticmethod
from collections.abc import Awaitable, Callable, Mapping
from typing import Iterable, Optional, Protocol, TypeVar, Union

import telethon
from telethon.tl.custom import Message

from tgmount import fs, tglog, vfs
from tgmount.tgclient.message_source import Subscribable
from tgmount.tgmount.error import TgmountError
from tgmount.util import none_fallback

from .tgmount_root_producer_types import Set
from .vfs_structure_types import PutEntity, VfsStructureBaseProto, VfsStructureProto

logger = tglog.getLogger("VfsStructure")
logger.setLevel(tglog.TRACE)

T = TypeVar("T")


def remove_from_list(items: list, func):
    for idx in [idx for idx, a in enumerate(items) if func(a)]:
        del items[idx]


class VfsStructureBase(VfsStructureBaseProto):
    """
    Represents a single folder with subfolders

    may contane subfolders
    """

    def __init__(self) -> None:
        """ """
        super().__init__()

        self._subdirs: dict[str, VfsStructureBaseProto] = {}
        self._content: list[PutEntity] = []

        self._by_vfs_stucture_path: dict["VfsStructureProto", str] = {}

        self._logger = logger

    def __repr__(self) -> str:
        return f"VfsStructureBase()"

    async def list_content(
        self,
    ) -> tuple[dict[str, VfsStructureBaseProto], list[vfs.DirContentItem]]:
        res: list[vfs.DirContentItem] = []

        subdirs = {**self._subdirs}

        for c in self._content:
            if isinstance(c, list):
                res.extend(c)
            else:
                _sd, _c = await c.list_content()
                subdirs.update(_sd)
                res.extend(_c)

        return (subdirs, res)

    async def put_subdir(
        self, dir_name: str, vfs_structure: "VfsStructure", *, generate_event=False
    ):
        self._by_vfs_stucture_path[vfs_structure] = dir_name
        self._subdirs[dir_name] = vfs_structure

    async def put_content(self, entity: PutEntity, *, generate_event=False):
        if isinstance(entity, VfsStructure):
            self._by_vfs_stucture_path[entity] = "/"

        self._content.append(entity)

    async def get_substructure(self, subitem: str) -> Optional[VfsStructureBaseProto]:
        if (item := self._subdirs.get(subitem)) is not None:
            return item

        for ent in self._content:
            if isinstance(ent, VfsStructure):
                if (item := await ent.get_substructure(subitem)) is not None:
                    return item

    async def get_by_path(
        self, path: list[str] | str
    ) -> Optional[VfsStructureBaseProto]:

        if isinstance(path, str):
            path = vfs.napp(path, noslash=True)

        if path == []:
            return self

        if path == ["/"]:
            return self

        [subitem, *rest] = path

        sub = await self.get_substructure(subitem)

        if sub is not None:
            return await sub.get_by_path(rest)

    async def put(self, path: str, entity: PutEntity, *, generate_event=False):
        """
        put('/existing', VfsStruct) # put_content
        put('/existing', [file1, file2]) # put_content
        put('/newdir', VfsStruct) # put_subdir
        put('/newdir', [file1, file2]) # throws

        """
        path = vfs.norm_path(path, addslash=True)

        parent_path = vfs.parent_path(path)
        name = os.path.basename(path)

        entity_by_path = await self.get_by_path(path)
        parent = await self.get_by_path(parent_path)

        if parent is None:
            raise TgmountError(f"Missing parent vfs_structure {parent_path}")

        if isinstance(entity, list):
            if entity_by_path is None:
                raise TgmountError(
                    f"Missing target vfs_structure {path} while putting content: {entity}. paths: {list(self._subdirs.keys())}"
                )

            await entity_by_path.put_content(entity, generate_event=generate_event)
        else:
            if entity_by_path is None:
                self._logger.info(f"put_subdir({name})")
                await parent.put_subdir(name, entity, generate_event=generate_event)
            else:
                self._logger.info(f"put_content(VfsStructure)")
                await entity_by_path.put_content(entity, generate_event=generate_event)

    async def remove_by_path(self, path: str):
        path = vfs.norm_path(path, addslash=True)
        parent_path = vfs.parent_path(path)
        name = os.path.basename(path)

        # entity_by_path = await self.get_by_path(path)
        parent = await self.get_by_path(parent_path)

        if parent:
            await parent.remove_subitem(name)

    async def remove_subitem(self, subitem: str):
        if subitem in self._subdirs:
            del self._subdirs[subitem]

        for c in self._content:
            if isinstance(c, list):
                remove_from_list(c, lambda a: a.name == subitem)
            else:
                await c.remove_subitem(subitem)


class VfsStructure(VfsStructureBase):
    def __init__(self) -> None:
        super().__init__()


class VfsStructureUpdaterContent:
    def __init__(self) -> None:
        pass

    async def put(self, path: str, vfs_structure: PutEntity):
        """
        Method used by producer to create the initial state of the structure or add
        """
        ...

    async def remove_by_path(self, path: str):
        ...


# class VfsStructureUpdater:
#     def __init__(self) -> None:
#         super().__init__()

#     async def __aenter__(self):
#         pass

#     async def __aexit__(self, exc_type, exc, tb):
#         pass

#     async def update(
#         self,
#         removed_dir_contents: list[str] | None = None,
#         removed_files: list[str] | None = None,
#         new_files: Mapping[str, vfs.FileLike] | None = None,
#     ):
#         update = fs.FileSystemOperationsUpdate()

#         for path in none_fallback(removed_dir_contents, []):
#             path = vfs.norm_path(path, True)
#             parent_path = os.path.dirname(path)

#             await self.remove_by_path(path)

#             update.removed_dir_contents.append(path)
#             update.update_dir_content[parent_path] = await self.get_dir_content_by_path(
#                 parent_path
#             )

#         for path in none_fallback(removed_files, []):
#             path = vfs.norm_path(path, True)
#             parent_path = os.path.dirname(path)

#             await self.remove_by_path(path)

#             update.removed_files.append(path)
#             update.update_dir_content[parent_path] = await self.get_dir_content_by_path(
#                 parent_path
#             )

#         for path, file in none_fallback(new_files, {}).items():
#             path = vfs.norm_path(path, True)
#             parent_path = os.path.dirname(path)

#             await self.put(parent_path, [file])

#             update.new_files[path] = file
#             update.update_dir_content[parent_path] = await self.get_dir_content_by_path(
#                 parent_path
#             )

#         await self.notify(update)
