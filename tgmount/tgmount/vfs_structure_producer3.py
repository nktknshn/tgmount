from abc import abstractmethod, abstractstaticmethod
from dataclasses import dataclass
import os
from collections.abc import Awaitable, Callable, Sequence
import telethon
from typing import (
    Any,
    Iterable,
    Mapping,
    Optional,
    Protocol,
    Type,
    TypeVar,
    TypedDict,
    Union,
)
from telethon.tl.custom import Message
from tgmount.tg_vfs.tree.helpers.by_user import group_by_sender
from tgmount.tg_vfs.tree.helpers.remove_empty import remove_empty_dirs_content
from tgmount.tgclient.message_source import (
    MessageSourceProto,
    MessageSourceSubscribableProto,
    Subscribable,
    TelegramMessageSourceSimple,
)
from tgmount.tgmount.error import TgmountError
from tgmount.tgmount.provider_sources import SourcesProvider
from tgmount.tgmount.vfs_structure_plain import sets_difference
from tgmount.tgmount.vfs_wrappers import VfsWrapperProto
from tgmount.tgmount.wrappers import ExcludeEmptyDirs, ZipsAsDirsWrapper

from tgmount.util import none_fallback


from tgmount import fs, tgclient, vfs, tglog, zip as z

from .tgmount_root_producer_types import (
    CreateRootContext,
    ProducerConfig,
    MessagesSet,
    Set,
    TgmountRootSource,
    VfsStructureConfig,
)
from .types import CreateRootResources, SourcesProviderProto
from .tgmount_root_config_reader import (
    TgmountConfigReader,
    TgmountConfigReader2,
    TgmountConfigReaderWalker,
)
from .vfs_structure_types import VfsStructureProducerProto, VfsStructureProto
from .vfs_structure import VfsStructure

logger = tglog.getLogger("VfsStructureProducer")
logger.setLevel(tglog.TRACE)


class VfsTreeProto:
    @abstractmethod
    async def create_dir(self, path: str):
        pass


class VfsTreeSubProto(Protocol):
    @abstractmethod
    async def produce(
        self,
    ):
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


VfsTreeDirContentList = Sequence[vfs.DirContentItem]


class VfsTreeDirProto(Protocol):
    pass


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

    # async def _list_content(self):
    #     vfs_items = await self.get_content()
    #     subdirs = await self.get_subdirs()

    #     return subdirs, vfs_items


# class VfsTreeDirChildProto(Protocol):
#     pass


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


class WrapperEmpty(Wrapper):
    def __init__(self, wrapped_dir: "VfsTreeDir") -> None:
        self._wrapped_dir = wrapped_dir
        self._wrapped_dir_subdirs: set["VfsTreeDir"] = set()
        # self._wrapped_dir_subdirs: set[str] | None = None

    async def wrap_dir_content(
        self, dir_content: vfs.DirContentProto
    ) -> vfs.DirContentProto:
        return remove_empty_dirs_content(dir_content)

    async def _get_subdirs_names(self, child: "VfsTreeDir") -> set[str]:
        return set(sd.name for sd in await child.get_subdirs())

    async def _is_empty(self, subdir: "VfsTreeDir") -> bool:
        sds = await subdir.get_subdirs()
        cs = await subdir.get_content()

        return (len(sds) + len(cs)) == 0

    async def wrap_updates(
        self,
        child: "VfsTreeDir",
        # child: Union["VfsTreeDir", "VfsTree"],
        updates: list[UpdateType],
    ) -> list[UpdateType]:
        # print(updates)
        parent = await child.get_parent()

        # we ignore nested folders
        if parent != self._wrapped_dir:
            return updates

        is_empty = await self._is_empty(child)
        # print(
        #     f"self={self._wrapped_dir.path} child={child.path} is_empty={is_empty} wrapped_subdirs={self._wrapped_dir_subdirs} updates={updates}"
        # )

        if child in self._wrapped_dir_subdirs:
            if is_empty:
                updates = [UpdateRemovedDirs(self._wrapped_dir.path, [child.path])]
        else:
            if not is_empty:
                updates = [
                    UpdateNewDirs(self._wrapped_dir.path, [child.path]),
                    *updates,
                ]
                self._wrapped_dir_subdirs.add(child)

        return updates
        # if self._wrapped_dir_subdirs is None:
        #     self._wrapped_dir_subdirs = await self._get_subdirs_names(child)
        # else:
        #     new_subdirs = await self._get_subdirs_names(child)

        # result = []

        # # we need to stop all events from excluded dirs
        # for u in updates:
        #     updated_dir = await self._wrapped_dir.tree.get_dir(u.update_path)
        #     updated_dir_parent = await updated_dir.get_parent()

        #     if updated_dir_parent != self._wrapped_dir:
        #         return updates
        #     # if isinstance(u, UpdateRemovedItems):
        #     #     continue
        #     # elif isinstance(u, UpdateNewItems):
        #     #     continue
        #     # elif isinstance(u, UpdateRemovedDirs):
        #     #     continue
        #     # elif isinstance(u, UpdateNewDirs):
        #     #     continue

        #     result.append(u)

        # return result


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


class VfsTreeExcludeEmpty:
    @staticmethod
    async def create(parent_tree: "VfsTreeParentProto", path: str):
        w = VfsTreeExcludeEmpty(parent_tree, path)

        await w._parent_tree.put_dir(w.dir_for_tree)
        await w._producer_tree.put_dir(w.dir_for_producer)

        return w

    def __init__(self, tree: "VfsTreeParentProto", path: str) -> None:
        self._parent_tree = tree
        self.dir_for_tree = VfsTreeDir(self._parent_tree, path)

        self._producer_tree = VfsTree()
        self.dir_for_producer = VfsTreeDir(self._producer_tree, "/")


class VfsTreeExcludeEmptyWrapper(VfsTreeDir):
    """
    We wrap VfsTreeDir by providing a fake VfsTree as parent.

    VfsTreeExcludeEmptyWrapper is a tree and a Dir at the same moment;

    It has two interface: first for the producer, second for the tree
    """

    def __init__(self, tree: "VfsTreeParentProto", path: str) -> None:
        self._parent_tree = tree
        self._path = path

        self._tree = VfsTree()
        self._dir = VfsTreeDir(self._tree, "/")
        self._tree.subscribe(self._wrapped_dir_update)

    def __repr__(self) -> str:
        return f"VfsTreeExcludeEmptyWrapper(path={self._path})"

    @property
    def name(self):
        return vfs.split_path(self._path)[1]

    @property
    def path(self):
        return self._path

    @property
    def _subs(self):
        return self._dir._subs

    @property
    def tree(self) -> "VfsTreeParentProto":
        return self._parent_tree

    async def _wrapped_dir_update(self, source, update):
        pass

    async def get_subdir(self, subpath: str) -> "VfsTreeDir":
        return await self._dir.get_subdir(subpath)

    async def get_subdirs(self, subpath: str = "/") -> list["VfsTreeDir"]:
        return await self._dir.get_subdirs(subpath)

    async def get_content(self, subpath: str = "/"):
        return await self._dir.get_content(subpath)

    async def create_dir(self, subpath: str) -> "VfsTreeDir":
        return await self._dir.create_dir(subpath)

    async def put_dir(self, d: VfsTreeDir) -> "VfsTreeDir":
        return await self._dir.put_dir(d)

    async def put_content(
        self,
        content: Sequence[vfs.DirContentItem],
        subpath: str = "/",
        *,
        overwright=False,
    ):
        await self._dir.put_content(content, subpath, overwright=overwright)

    async def remove_subdir(self, subpath: str):
        await self._dir.remove_subdir(subpath)

    async def remove_content(
        self,
        item: vfs.DirContentItem,
        subpath: str = "/",
    ):
        await self._dir.remove_content(item, subpath)

    async def list_content(self):
        vfs_items = await self._dir.get_content()
        subdirs = await self._dir.get_subdirs()

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


class VfsTreeProducer:
    def __init__(self, resources: CreateRootResources) -> None:

        self._logger = logger

        # self._dir_config = dir_config
        self._resources = resources

    def __repr__(self) -> str:
        return f"VfsTreeProducer()"

    async def produce(
        self, tree_dir: VfsTreeDir | VfsTree, dir_config: TgmountRootSource, ctx=None
    ):
        config_reader = TgmountConfigReader()

        for (path, keys, vfs_config, ctx) in config_reader.walk_config_with_ctx(
            dir_config,
            resources=self._resources,
            ctx=none_fallback(ctx, CreateRootContext.from_resources(self._resources)),
        ):
            self._logger.info(f"produce: {vfs.path_join(tree_dir.path, path)}")

            if vfs_config.source_dict.get("wrappers") == "ExcludeEmptyDirs":
                # print(vfs_config.source_dict.get("wrappers"))
                sub_dir = await tree_dir.create_dir(path)
                sub_dir._wrappers.append(WrapperEmpty(sub_dir))
            elif vfs_config.source_dict.get("wrappers") == "ZipsAsDirs":
                # print(vfs_config.source_dict.get("wrappers"))
                sub_dir = await tree_dir.create_dir(path)
                # sub_dir._wrappers.append(z.ZipsAsDirs)
            else:
                sub_dir = await tree_dir.create_dir(path)

            if (
                vfs_config.producer_config
                and vfs_config.vfs_producer_name
                and vfs_config.vfs_producer_name == "MessageBySender"
            ):
                producer_arg = none_fallback(vfs_config.vfs_producer_arg, {})
                producer = VfsTreeDirByUser(
                    config=vfs_config.producer_config,
                    dir_cfg=producer_arg.get(
                        "sender_root",
                        VfsTreeDirByUser.DEFAULT_SENDER_ROOT_CONFIG,
                    ),
                    minimum=producer_arg.get("minimum", 1),
                    resources=self._resources,
                    tree_dir=sub_dir,
                )

                sub_dir._subs.append(producer)

                await producer.produce()
            elif vfs_config.producer_config:
                producer = VfsTreePlainDir(sub_dir, vfs_config.producer_config)

                sub_dir._subs.append(producer)

                await producer.produce()

            # sub_vfs_struct_producer = vfs_config.vfs_producer.from_config(
            #     self,
            #     self._resources,
            #     vfs_config,
            #     vfs_config.vfs_producer_arg,
            # )

            # self._by_path_producers[path] = sub_vfs_struct_producer
            # self._by_producer_path[sub_vfs_struct_producer] = path

            # await sub_vfs_struct_producer.produce_vfs_struct()

            # self.wrappers[path] = vfs_config.vfs_wrappers
            # for w in vfs_config.vfs_wrappers:
            #     self._logger.info(f"Wrapping at {path}")
            #     _vfs_structure = await w.wrap_vfs_structure(_vfs_structure)
            # await self._vfs_structure.put(path, _vfs_structure)


class VfsTreePlainDir(VfsTreeSubProto):
    def __init__(self, dir: VfsTreeDir, config: ProducerConfig) -> None:
        self._config = config
        self._dir = dir

        self._messages = MessagesSet()
        self._message_to_file: dict[str, vfs.FileLike] = {}

    async def produce(self):
        self._messages = await self._config.get_messages()
        self._message_to_file = {
            m: self._config.factory.file(m) for m in self._messages
        }

        if len(self._message_to_file) > 0:
            await self._dir.put_content(list(self._message_to_file.values()))

        self._config.message_source.subscribe(self.update)

    async def update(self, source, messages: list[Message]):
        messages_set = await self._config.apply_all_filters(messages)

        removed_messages, new_messages, common_messages = sets_difference(
            self._messages, messages_set
        )

        removed_files = [self._message_to_file[m] for m in removed_messages]
        old_files = [self._message_to_file[m] for m in common_messages]
        new_files: list[vfs.FileLike] = [
            self._config.factory.file(m) for m in new_messages
        ]

        self._messages = messages_set
        self._message_to_file = {
            **{m: f for m, f in zip(new_messages, new_files)},
            **{m: f for m, f in zip(common_messages, old_files)},
        }

        for f in removed_files:
            await self._dir.remove_content(f)

        if len(new_files):
            await self._dir.put_content(new_files)


class VfsTreeDirByUser(VfsTreeSubProto):
    MessageSource = TelegramMessageSourceSimple
    DEFAULT_SENDER_ROOT_CONFIG = {"filter": "All"}
    VfsTreeProducer = VfsTreeProducer

    def __init__(
        self,
        tree_dir: VfsTreeDir,
        config: ProducerConfig,
        *,
        minimum=1,
        resources: CreateRootResources,
        dir_cfg=DEFAULT_SENDER_ROOT_CONFIG,
    ) -> None:
        self._config = config
        self._dir = tree_dir

        self._minimum = minimum
        self._resources = resources
        self._dir_cfg = dir_cfg

        self._source_by_name: dict[str, VfsTreeDirByUser.MessageSource] = {}
        self._source_less = self.MessageSource()

    async def add_user_dir(self, user_name: str, user_messages: Set[Message]):
        user_source = self.MessageSource(messages=user_messages)
        user_dir = await self._dir.create_dir(user_name)

        await self.VfsTreeProducer(self._resources).produce(
            user_dir,
            self._dir_cfg,
            ctx=CreateRootContext.from_resources(
                self._resources, recursive_source=user_source
            ),
        )

        self._source_by_name[user_name] = user_source

    async def produce(self):

        messages = await self._config.message_source.get_messages()

        by_user, less, nones = await group_by_sender(
            messages,
            minimum=self._minimum,
        )

        for user_name, user_messages in by_user.items():
            await self.add_user_dir(user_name, Set(user_messages))

        await self._source_less.set_messages(Set(less))

        less_sub = VfsTreePlainDir(
            self._dir, self._config.set_message_source(self._source_less)
        )

        self._dir._subs.append(less_sub)

        await less_sub.produce()

        self._config.message_source.subscribe(self.update)

    async def update(self, source, messages: list[Message]):
        by_user, less, nones = await group_by_sender(
            messages,
            minimum=self._minimum,
        )

        current_dirs = Set(self._source_by_name.keys())

        removed_dirs, new_dirs, common_dirs = sets_difference(
            current_dirs, Set(by_user.keys())
        )

        await self._source_less.set_messages(Set(less))

        for d in removed_dirs:
            await self._dir.remove_subdir(d)
            del self._source_by_name[d]

        for d in new_dirs:
            await self.add_user_dir(d, Set(by_user[d]))

        for d in common_dirs:
            _source = self._source_by_name[d]
            await _source.set_messages(Set(by_user[d]))


class SourcesProviderMessageSource(
    Subscribable, tgclient.MessageSourceSubscribableProto
):
    """
    Wraps MessageSource to accumulate updates in the tree that were triggered
    by parent message source
    """

    def __init__(
        self, tree: VfsTree, source: tgclient.MessageSourceSubscribableProto
    ) -> None:
        Subscribable.__init__(self)
        self._source = source
        self._tree = tree
        self._source.subscribe(self.on_update)

        self.updates = Subscribable()

    async def get_messages(self) -> list[Message]:
        return await self._source.get_messages()

    async def on_update(self, source, messages):

        _updates = []

        async def append_update(source, updates: list[UpdateType]):
            _updates.extend(updates)

        self._tree.subscribe(append_update)

        await self.notify(messages)

        self._tree.unsubscribe(append_update)

        await self.updates.notify(_updates)


class SourcesProviderAccumulating(SourcesProvider[SourcesProviderMessageSource]):
    """
    Wraps MessageSource to accumulate updates in the tree that were triggered
    by parent message source before passing them to FS
    """

    def __init__(
        self,
        tree: VfsTree,
        source_map: Mapping[str, tgclient.MessageSourceSubscribableProto],
    ) -> None:

        self.updates = Subscribable()
        self._tree = tree

        super().__init__(
            {
                k: SourcesProviderMessageSource(self._tree, v)
                for k, v in source_map.items()
            }
        )

        for k, v in self._source_map.items():
            v.updates.subscribe(self.updates.notify)
