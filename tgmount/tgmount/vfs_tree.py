from abc import abstractmethod
from dataclasses import dataclass
from collections.abc import Sequence
from typing import Protocol, Union
from tgmount.tgclient.message_source import Subscribable
from tgmount.tgmount.error import TgmountError
from tgmount.util import none_fallback
from tgmount import vfs, tglog, zip as z


logger = tglog.getLogger("VfsStructureProducer")
logger.setLevel(tglog.TRACE)


class VfsTreeProto:
    @abstractmethod
    async def create_dir(self, path: str):
        pass


class VfsTreeSubProto(Protocol):
    @abstractmethod
    async def produce(self):
        ...


class VfsTreeDirContent(vfs.DirContentProto):
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


@dataclass
class UpdateRemovedItems:
    update_path: str
    removed_items: list[vfs.DirContentItem]


@dataclass
class UpdateNewItems:
    update_path: str
    new_items: list[vfs.DirContentItem]


@dataclass
class UpdateRemovedDirs:
    update_path: str
    removed_dirs: list[str]


@dataclass
class UpdateNewDirs:
    update_path: str
    new_dirs: list[str]


UpdateType = UpdateRemovedItems | UpdateNewItems | UpdateRemovedDirs | UpdateNewDirs


class Wrapper:
    def __init__(self) -> None:
        pass

    async def wrap_dir_content(
        self, dir_content: vfs.DirContentProto
    ) -> vfs.DirContentProto:
        ...

    async def wrap_updates(
        self, child: Union["VfsTreeDir", "VfsTree"], updates: list[UpdateType]
    ) -> list[UpdateType]:
        ...


class VfsTreeParentProto(Protocol):
    @abstractmethod
    async def remove_content(self, path: str, item: vfs.DirContentItem):
        ...

    @abstractmethod
    async def put_content(
        self,
        content: Sequence[vfs.DirContentItem],
        path: str = "/",
        *,
        overwright=False,
    ):
        ...

    @abstractmethod
    async def remove_dir(self, path: str):
        ...

    @abstractmethod
    async def create_dir(self, path: str) -> "VfsTreeDir":
        ...

    @abstractmethod
    async def get_content(self, subpath: str) -> list[vfs.DirContentItem]:
        ...

    @abstractmethod
    async def get_dir(self, path: str) -> "VfsTreeDir":
        ...

    @abstractmethod
    async def get_subdirs(self, path: str, *, recusrive=False) -> list["VfsTreeDir"]:
        ...

    @abstractmethod
    async def put_dir(self, d: "VfsTreeDir") -> "VfsTreeDir":
        ...

    @abstractmethod
    async def get_parent(self, path: str) -> Union["VfsTreeDir", "VfsTree"]:

        ...

    @abstractmethod
    async def child_updated(
        self, child: Union["VfsTreeDir", "VfsTree"], updates: list[UpdateType]
    ):
        ...


class VfsTreeDirMixin:
    async def _put_content(
        self: "VfsTreeDir",
        content: Sequence[vfs.DirContentItem],
        path: str = "/",
        *,
        overwright=False,
    ):
        if overwright:
            self._content = list(content)
        else:
            self._content.extend(content)

    async def _get_content(self: "VfsTreeDir", subpath: str):
        return self._content[:]

    async def _remove_from_content(
        self,
        item: vfs.DirContentItem,
    ):
        self._content.remove(item)


class VfsTreeDir(VfsTreeDirMixin):
    def __init__(
        self,
        tree: "VfsTreeParentProto",
        path: str,
        wrappers=None,
        # subs are the users of the dir
        subs: list[VfsTreeSubProto] | None = None,
    ) -> None:
        self._parent_tree = tree
        self._wrappers: list[Wrapper] = none_fallback(wrappers, [])
        self._path = path
        self._content: list[vfs.DirContentItem] = []
        self._subs = none_fallback(subs, [])

    async def child_updated(
        self, child: Union["VfsTreeDir", "VfsTree"], updates: list[UpdateType]
    ):
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
    def tree(self) -> "VfsTreeParentProto":
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

    def add_sub_producer(self, sub: VfsTreeSubProto):
        self._subs.append(sub)

    async def produce(self):
        for s in self._subs:
            await s.produce()

    async def get_subdir(self, subpath: str) -> "VfsTreeDir":
        return await self._parent_tree.get_dir(self._globalpath(subpath))

    async def get_subdirs(self, subpath: str = "/") -> list["VfsTreeDir"]:
        return await self._parent_tree.get_subdirs(self._globalpath(subpath))

    async def get_content(self, subpath: str = "/"):
        return await self._parent_tree.get_content(self._globalpath(subpath))

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

    async def list_content(self):
        vfs_items = await self.get_content()
        subdirs = await self.get_subdirs()

        return subdirs, vfs_items


class VfsTree(Subscribable, VfsTreeProto):
    """
    The structure that holds the whole generated FS tree
    Producers use it to read and write the structures they represent

    We try to avoid recursivness
    """

    VfsTreeDir = VfsTreeDir
    VfsTreeDirContent = VfsTreeDirContent

    def __init__(self) -> None:
        Subscribable.__init__(self)

        self._logger = logger
        self._dirs: dict[str, VfsTreeDir] = {}
        self._path_dy_dir: dict[VfsTreeDir, str] = {}

    def __repr__(self) -> str:
        return f"VfsTree()"

    @property
    def path(self):
        return "/"

    @property
    def tree(self) -> VfsTreeParentProto:
        return self

    async def child_updated(self, child, updates: list[UpdateType]):
        await self.notify(updates)

    async def get_parents(
        self, path_or_dir: str | VfsTreeDir
    ) -> list[Union[VfsTreeDir, "VfsTree"]]:

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

        if path == "/":
            return self

        parent_dir, dir_name = vfs.split_path(path, addslash=True)
        return await self.get_dir(parent_dir)

    async def remove_content(
        self,
        path: str,
        item: vfs.DirContentItem,
    ):
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
        sd = await self.get_dir(path)

        await sd._put_content(content, overwright=overwright)

        await sd.child_updated(
            sd, [UpdateNewItems(update_path=path, new_items=list(content))]
        )

    async def remove_dir(self, path: str):
        thedir = await self.get_dir(path)
        subdirs = await self.get_subdirs(path, recusrive=True)
        parent_dir, dir_name = vfs.split_path(path, addslash=True)
        parent = await self.get_parent(path)

        for sd in subdirs:
            del self._dirs[sd.path]
            del self._path_dy_dir[sd]

        del self._dirs[path]
        del self._path_dy_dir[thedir]

        await parent.child_updated(
            parent, [UpdateRemovedDirs(update_path=parent_dir, removed_dirs=[path])]
        )

    async def create_dir(self, path: str) -> VfsTreeDir:
        path = vfs.norm_path(path, addslash=True)
        parent_dir, dir_name = vfs.split_path(path, addslash=True)
        parent = await self.get_parent(path)

        if path in self._dirs:
            return self._dirs[path]
            # raise TgmountError(f"Directory {path} is already created")

        if path != "/" and parent_dir not in self._dirs:
            await self.create_dir(parent_dir)

        self._dirs[path] = self.VfsTreeDir(self, path)
        self._path_dy_dir[self._dirs[path]] = path

        await parent.child_updated(
            parent, [UpdateNewDirs(update_path=parent_dir, new_dirs=[path])]
        )

        return self._dirs[path]

    async def put_dir(self, d: VfsTreeDir) -> VfsTreeDir:
        path = vfs.norm_path(d.path, addslash=True)
        parent_dir, dir_name = vfs.split_path(path, addslash=True)
        parent = await self.get_parent(path)

        if path in self._dirs:
            self._dirs[path] = d
            self._path_dy_dir[d] = path
            return self._dirs[path]

        if path != "/" and parent_dir not in self._dirs:
            await self.create_dir(parent_dir)

        self._dirs[path] = d
        self._path_dy_dir[d] = path

        await parent.child_updated(
            parent, [UpdateNewDirs(update_path=parent_dir, new_dirs=[path])]
        )

        return self._dirs[path]

    async def get_content(self, subpath: str) -> list[vfs.DirContentItem]:
        sd = await self.get_dir(subpath)
        return sd._content[:]

    async def _get_dir_content(self, path: str):
        d = await self.get_dir(path)

        subdirs, vfs_items = await d.list_content()

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

    async def get_dir(self, path: str):
        if path not in self._dirs:
            raise TgmountError(f"Missing directory {path}")

        return self._dirs[path]

    async def get_subdirs(self, path: str, *, recusrive=False):
        res = []

        for p, d in self._dirs.items():
            if p == "/":
                continue

            if recusrive:
                if p.startswith(path + "/"):
                    res.append(d)
            else:
                (parent, name) = vfs.split_path(p)
                if parent == path:
                    res.append(d)

        return res

    async def get_dir_content(self, path: str = "/") -> VfsTreeDirContent:
        return VfsTreeDirContent(self, path)
