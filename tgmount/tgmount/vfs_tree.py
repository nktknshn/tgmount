from collections.abc import Mapping, Sequence
from typing import Union

from tgmount import vfs, tglog
from tgmount.tgclient.message_source import Subscribable
from tgmount.tgmount.error import TgmountError
from tgmount.tgmount.vfs_tree_types import (
    VfsTreeProto,
    UpdateRemovedItems,
    UpdateNewItems,
    UpdateRemovedDirs,
    UpdateNewDirs,
    UpdateType,
    Wrapper,
)
from tgmount.util import none_fallback
from tgmount.tgmount.vfs_tree_producer_types import VfsTreeProducerProto


logger = tglog.getLogger("VfsStructureProducer")
logger.setLevel(tglog.TRACE)


class VfsTreeDirContent(vfs.DirContentProto):
    """`vfs.DirContentProto` sourced from dir stored in `VfsTree` at `path`."""

    def __init__(self, tree: "VfsTree", path: str) -> None:
        self._tree = tree
        self._path = path

        # print(f"VfsTreeDirContent.init({self._path})")

    def __repr__(self) -> str:
        return f"VfsTreeDirContent({self._path})"

    async def _dir_content(self) -> vfs.DirContentProto:
        return await self._tree._get_dir_content(self._path)

    async def readdir_func(self, handle, off: int):
        # logger.info(f"ProducedContentDirContent({self._path}).readdir_func({off})")
        return await (await self._dir_content()).readdir_func(handle, off)

    async def opendir_func(self):
        # logger.info(f"ProducedContentDirContent({self._path}).opendir_func()")
        return await (await self._dir_content()).opendir_func()

    async def releasedir_func(self, handle):
        # logger.info(f"ProducedContentDirContent({self._path}).releasedir_func()")
        return await (await self._dir_content()).releasedir_func(handle)


class VfsTreeDirMixin:
    async def _put_content(
        self: "VfsTreeDir",
        content: Sequence[vfs.DirContentItem],
        path: str = "/",
        *,
        overwright=False,
    ):
        if overwright:
            self._dir_content_items = list(content)
        else:
            self._dir_content_items.extend(content)

    async def _get_dir_content_items(self: "VfsTreeDir"):
        return self._dir_content_items[:]

    async def _remove_from_content(
        self,
        item: vfs.DirContentItem,
    ):
        self._dir_content_items.remove(item)


class VfsTreeDir(VfsTreeDirMixin):
    """
    Represents a single dir.

    Holds wrappers and dir content items.
    """

    def __init__(
        self,
        tree: "VfsTree",
        path: str,
        wrappers=None,
        # subs are the users of the dir
        subs: list[VfsTreeProducerProto] | None = None,
    ) -> None:
        self._parent_tree = tree
        self._path = path
        self._wrappers: list[Wrapper] = none_fallback(wrappers, [])
        self._dir_content_items: list[vfs.DirContentItem] = []
        self._subs = none_fallback(subs, [])

    async def child_updated(self, child: "VfsTreeDir", updates: list[UpdateType]):
        """Method used by directory subdirs to notify it about its modifications. If this dir contains any wrappers updates are wrapped with `wrap_updates` method."""
        parent = await self.get_parent()

        # print(f"{self.path} child_updated({child.path}, {updates})")
        # print(self.path)
        # print(await self._parent_tree.get_parents(child))

        for w in self._wrappers:
            updates = await w.wrap_updates(child, updates)

        await parent.child_updated(child, updates)

    async def get_parent(self):

        if self.path == "/":
            return self._parent_tree

        return await self._parent_tree.get_parent(self._path)

    def __repr__(self) -> str:
        return f"VfsTreeDir(path={self._path})"

    @property
    def tree(self) -> "VfsTree":
        return self._parent_tree

    @property
    def name(self):
        return vfs.split_path(self._path)[1]

    @property
    def path(self):
        return self._path

    def _globalpath(self, subpath: str):
        if subpath == "/":
            return self._path

        return vfs.path_join(self._path, vfs.path_remove_slash(subpath))

    def add_sub_producer(self, sub: VfsTreeProducerProto):
        self._subs.append(sub)

    async def produce(self):
        for s in self._subs:
            await s.produce()

    async def get_subdir(self, subpath: str) -> "VfsTreeDir":
        return await self._parent_tree.get_dir(self._globalpath(subpath))

    async def get_subdirs(self, subpath: str = "/") -> list["VfsTreeDir"]:
        return await self._parent_tree.get_subdirs(self._globalpath(subpath))

    async def get_dir_content_items(self, subpath: str = "/"):
        return await self._parent_tree.get_dir_content_items(self._globalpath(subpath))

    async def create_dir(self, subpath: str) -> "VfsTreeDir":
        return await self._parent_tree.create_dir(self._globalpath(subpath))

    async def put_dir(self, d: "VfsTreeDir") -> "VfsTreeDir":
        return await self._parent_tree.put_dir(d)

    async def put_content(
        self,
        content: Sequence[vfs.DirContentItem],
        subpath: str = "/",
        *,
        overwright=False,
    ):
        await self._parent_tree.put_content(
            content, self._globalpath(subpath), overwright=overwright
        )

    async def remove_subdir(self, subpath: str):
        await self._parent_tree.remove_dir(self._globalpath(subpath))

    async def remove_content(
        self,
        item: vfs.DirContentItem,
        subpath: str = "/",
    ):
        await self._parent_tree.remove_content(self._globalpath(subpath), item)

    # async def list_content(self):
    #     vfs_items = await self.get_dir_content_items()
    #     subdirs = await self.get_subdirs()

    #     return subdirs, vfs_items


class SubdirsRegistry:
    """Stores mapping path -> list[path]"""

    def __init__(self) -> None:
        self._subdirs_by_path: dict[str, list[str]] = {}

    def add_path(self, path: str):
        """"""

        if path in self._subdirs_by_path:
            raise TgmountError(f"SubdirsRegistry: {path} is already in registry")

        self._subdirs_by_path[path] = []

        parent, name = vfs.split_path(path)

        if name == "":
            return

        if parent not in self._subdirs_by_path:
            raise TgmountError(
                f"SubdirsRegistry: error putting {path}. Missing parent {parent} in registry"
            )

        self._subdirs_by_path[parent].append(path)

    def remote_path(self, path: str):
        pass

    def get_subdirs(self, path: str, recursive=False) -> list[str]:
        subs = self._subdirs_by_path.get(path)

        if subs is None:
            raise TgmountError(f"SubdirsRegistry: Missing {path} in registry")

        # subs = subs[:]
        subssubs = []

        if recursive:
            for s in subs:
                subssubs.extend(self.get_subdirs(s, recursive=True))

        return [*subs, *subssubs]


class VfsTree(Subscribable, VfsTreeProto):
    """
    The structure that holds the whole generated FS tree.
    Producers use it to read and write the structures they are responsible for.

    Storing dirs in a single mappig we try to avoid recursivness.

    Provides interface for accessing dirs and their contents by their global paths.
    """

    VfsTreeDir = VfsTreeDir
    VfsTreeDirContent = VfsTreeDirContent

    def __init__(self) -> None:
        Subscribable.__init__(self)

        self._logger = logger
        self._dirs: dict[str, VfsTreeDir] = {}
        self._path_dy_dir: dict[VfsTreeDir, str] = {}
        self._subdirs = SubdirsRegistry()

    def __repr__(self) -> str:
        return f"VfsTree()"

    @property
    def path(self):
        return "/"

    @property
    def tree(self) -> VfsTreeProto:
        return self

    async def child_updated(self, child, updates: list[UpdateType]):
        """Notifies tree subscribers with subchild `updates`"""
        await self.notify(updates)

    async def remove_content(
        self,
        path: str,
        item: vfs.DirContentItem,
    ):
        """Removes `item` from `path` notifying parent dir with `UpdateRemovedItems`."""
        sd = await self.get_dir(path)

        await sd._remove_from_content(item)

        await sd.child_updated(
            sd, [UpdateRemovedItems(update_path=path, removed_items=[item])]
        )

    async def put_content(
        self,
        content: Sequence[vfs.DirContentItem],
        path: str = "/",
        *,
        overwright=False,
    ):
        """Put a sequence of `vfs.DirContentItem` at `path`."""
        sd = await self.get_dir(path)

        await sd._put_content(content, overwright=overwright)

        await sd.child_updated(
            sd, [UpdateNewItems(update_path=path, new_items=list(content))]
        )

    async def remove_dir(self, path: str):
        """Removes a dir stored at `path` notifying parent dir with `UpdateRemovedDirs`."""

        if path == "/":
            raise TgmountError(f"Cannot remove root folder.")

        thedir = await self.get_dir(path)
        subdirs = await self.get_subdirs(path, recursive=True)

        # parent_dir, dir_name = vfs.split_path(path, addslash=True)
        parent = await self.get_parent(path)

        for sd in subdirs:
            del self._dirs[sd.path]
            del self._path_dy_dir[sd]

        del self._dirs[path]
        del self._path_dy_dir[thedir]

        self._subdirs.remote_path(path)

        await parent.child_updated(
            parent,
            [UpdateRemovedDirs(update_path=parent.path, removed_dirs=[path])],
        )

    async def create_dir(self, path: str) -> VfsTreeDir:
        """Creates a subdir at `path`. Notifies parent dir with `UpdateNewDirs` and returns created `VfsTreeDir`"""
        return await self.put_dir(self.VfsTreeDir(self, path))

    async def put_dir(self, d: VfsTreeDir) -> VfsTreeDir:
        """Put `VfsTreeDir`. May be used instead of `create_dir` method."""
        path = vfs.norm_path(d.path, addslash=True)
        # parent_dir, dir_name = vfs.split_path(path, addslash=True)
        parent = await self.get_parent(path)

        if path in self._dirs:
            self._dirs[path] = d
            self._path_dy_dir[d] = path
            return self._dirs[path]

        if path != "/" and parent.path not in self._dirs:
            await self.create_dir(parent.path)

        self._dirs[path] = d
        self._path_dy_dir[d] = path
        self._subdirs.add_path(path)

        await parent.child_updated(
            parent,
            [UpdateNewDirs(update_path=parent.path, new_dirs=[path])],
        )

        return self._dirs[path]

    async def get_parents(
        self, path_or_dir: str | VfsTreeDir
    ) -> list[Union[VfsTreeDir, "VfsTree"]]:
        """ "Returns a list of parents of `path_or_dir` with first element being `VfsTree`"""

        if path_or_dir == "/":
            return [self]

        if isinstance(path_or_dir, str):
            path = path_or_dir
            thedir = await self.get_dir(path_or_dir)
        else:
            path = path_or_dir.path
            thedir = path_or_dir

        parent = await self.get_parent(path)
        result = [parent]

        while parent != self:
            parent = await self.get_parent(parent.path)
            result.append(parent)

        return result

    async def get_parent(self, path: str) -> Union[VfsTreeDir, "VfsTree"]:
        """Returns parent `VfsTreeDir` for dir at `path`. Returns `VfsTree` for `path == '/'`"""

        if path == "/":
            return self

        parent_dir, dir_name = vfs.split_path(path, addslash=True)
        return await self.get_dir(parent_dir)

    async def get_dir_content_items(self, subpath: str) -> list[vfs.DirContentItem]:
        """Returns a list of `vfs.DirContentItem` stored at `path`"""
        sd = await self.get_dir(subpath)
        return await sd._get_dir_content_items()

    async def get_dir(self, path: str) -> "VfsTreeDir":
        """Returns `VfsTreeDir` stored at `path`"""
        if path not in self._dirs:
            raise TgmountError(f"Missing directory {path}")

        return self._dirs[path]

    async def get_subdirs(self, path: str, *, recursive=False) -> list[VfsTreeDir]:
        """Returns a list of `VfsTreeDir` which are subdirs of dir stored at `path`. If `recursive` flag is set all the nested subdirs are included."""
        res = []

        subdirs = self._subdirs.get_subdirs(path, recursive)

        for s in subdirs:
            res.append(self._dirs[s])
        # for p, d in self._dirs.items():
        #     if p == "/":
        #         continue

        #     if recursive:
        #         if p.startswith(path + "/"):
        #             res.append(d)
        #     else:
        #         (parent, name) = vfs.split_path(p)
        #         if parent == path:
        #             res.append(d)

        return res

    async def get_dir_content(self, path: str = "/") -> VfsTreeDirContent:
        """Returns `VfsTreeDirContent`"""
        return VfsTreeDirContent(self, path)

    async def _get_dir_content(self, path: str) -> vfs.DirContentProto:
        """Method used by `VfsTreeDirContent` to construct `vfs.DirContentProto`"""
        d = await self.get_dir(path)

        vfs_items, subdirs = (
            await d.get_dir_content_items(),
            await d.get_subdirs(),
        )

        content = [
            *vfs_items,
            *[
                vfs.vdir(sd.name, self.VfsTreeDirContent(self, sd.path))
                for sd in subdirs
            ],
        ]

        dc: vfs.DirContentProto = vfs.dir_content(*content)

        for w in d._wrappers:
            dc = await w.wrap_dir_content(dc)

        return dc
