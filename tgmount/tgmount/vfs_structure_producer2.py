from abc import abstractmethod, abstractstaticmethod
import os
from collections.abc import Awaitable, Callable
import telethon
from typing import Iterable, Optional, Protocol, TypeVar
from telethon.tl.custom import Message
from tgmount.tgclient.message_source import (
    MessageSourceProto,
    MessageSourceSubscribableProto,
    Subscribable,
)
from tgmount.tgmount.error import TgmountError
from tgmount.tgmount.vfs_wrappers import VfsWrapperProto

from tgmount.util import none_fallback


from tgmount import fs, vfs, tglog

from .tgmount_root_producer_types import (
    CreateRootContext,
    ProducerConfig,
    MessagesSet,
    Set,
    TgmountRootSource,
    VfsStructureConfig,
)
from .types import CreateRootResources
from .tgmount_root_config_reader import (
    TgmountConfigReader,
    TgmountConfigReader2,
    TgmountConfigReaderWalker,
)
from .vfs_structure_types import VfsStructureProducerProto, VfsStructureProto
from .vfs_structure import VfsStructure

logger = tglog.getLogger("VfsStructureProducer")
logger.setLevel(tglog.TRACE)


class VfsStructureRoot:
    def __init__(self) -> None:
        pass


class VfsStructureProducerDirContent(vfs.DirContentProto):
    def __init__(self, producer: "VfsStructureFromConfigProducer", path: str) -> None:
        self._producer = producer
        self._path = path

    async def _dir_content(self) -> vfs.DirContentProto:
        vs = await self._producer.get_vfs_structure_by_path(self._path)

        vs_subdirs, vs_content = await vs.list_content()
        content = vs_content

        for subdir_name, subdir_content in vs_subdirs.items():
            content.append(
                vfs.vdir(
                    subdir_name,
                    VfsStructureProducerDirContent(
                        self._producer,
                        os.path.join(self._path, subdir_name),
                    ),
                )
            )

        return vfs.dir_content(*content)

    async def readdir_func(self, handle, off: int):
        # logger.info(f"ProducedContentDirContent({self._path}).readdir_func({off})")
        return await (await self._dir_content()).readdir_func(handle, off)

    async def opendir_func(self):
        # logger.info(f"ProducedContentDirContent({self._path}).opendir_func()")
        return await (await self._dir_content()).opendir_func()

    async def releasedir_func(self, handle):
        # logger.info(f"ProducedContentDirContent({self._path}).releasedir_func()")
        return await (await self._dir_content()).releasedir_func(handle)


class VfsStructureFromConfigProducerVfsStructe(VfsStructureProto):
    def __init__(self, producer: "VfsStructureFromConfigProducer", path: str) -> None:
        self._producer = producer
        self._path = path

    def __repr__(self) -> str:
        return (
            f"VfsStructureFromConfigProducerVfsStructe({self._producer}, {self._path})"
        )

    async def original(self):
        return await self._producer.get_vfs_structure_by_path(self._path)

    async def list_content(
        self,
    ) -> tuple[dict[str, "VfsStructureProto"], list[vfs.DirContentItem],]:
        vs = await self._producer.get_vfs_structure_by_path(self._path)

        subdirs = {}

        _subdirs, _content = await vs.list_content()

        for subdir_name, subdir_content in _subdirs.items():
            subdirs[subdir_name] = VfsStructureFromConfigProducerVfsStructe(
                self._producer, os.path.join(self._path, subdir_name)
            )

        return subdirs, _content


class VfsStructureFromConfigProducer(Subscribable, VfsStructureProducerProto):
    def __init__(
        self, dir_config: TgmountRootSource, resources: CreateRootResources
    ) -> None:

        Subscribable.__init__(self)

        self._logger = logger

        self._dir_config = dir_config
        self._resources = resources

        self._by_path_producers: dict[str, VfsStructureProducerProto] = {}
        self._by_producer_path: dict[VfsStructureProducerProto, str] = {}

        self.wrappers: dict[str, list[VfsWrapperProto]] = {}
        self.wrappers_state: dict[str, dict[VfsWrapperProto, dict]] = {}

    def __repr__(self) -> str:
        return f"VfsStructureFromConfigProducer()"

    def get_vfs_structure(self):
        return VfsStructureFromConfigProducerVfsStructe(self, "/")

    async def get_dir_content(self, path: str = "/") -> vfs.DirContentProto:
        return VfsStructureProducerDirContent(self, path)

    def get_wrapper_state(self, path: str, w: VfsWrapperProto):
        ws_state = self.wrappers_state.get(path, {})
        self.wrappers_state[path] = ws_state
        w_state = ws_state.get(w, {})
        ws_state[w] = w_state

        return w_state

    async def get_vfs_structure_by_path(self, path: str):
        vs = self._by_path_producers[path].get_vfs_structure()

        if vs is None:
            raise TgmountError(f"Missing vfs structure at {path}")

        for p, ws in self.get_wrappers(path):
            for w in ws:
                vs = await w.wrap_vfs_structure(self.get_wrapper_state(path, w), vs)

        return vs

    def get_wrappers(self, path: str):
        for p, w in self.wrappers.items():
            if path.startswith(p):
                yield p, w

    async def on_child_update(
        self,
        subproducer: "VfsStructureProducerProto",
        update: fs.FileSystemOperationsUpdate,
    ):

        sub_path = self._by_producer_path.get(subproducer)

        if sub_path is None:
            raise TgmountError(f"Missing subproducer: {subproducer}")

        # sub_vfs = await self._vfs_structure.get_by_path(sub_path)

        # if sub_vfs is None:
        #     raise TgmountError(f"Missing vfs structure at: {sub_path}")

        self._logger.info(f"update at {sub_path}: {update}")

        # prepended = ""

        # for prod_path, prod in reversed(self._by_path_producers.items()):

        #     prod_vfs = VfsStructureFromConfigProducerVfsStructe(self, prod_path)

        #     if sub_path.startswith(prod_path):
        #         sub_path_path = sub_path[
        #             len(prod_path) : len(sub_path) - len(prepended)
        #         ]

        #         self._logger.info(f"Wrapping at {prod_path} {sub_path_path}")

        #         update = update.prepend_paths(sub_path_path)
        #         prepended += sub_path_path

        #         for w in self.wrappers.get(prod_path, []):
        #             w_state = self.get_wrapper_state(prod_path, w)
        #             update = await w.wrap_update(w_state, prod_vfs, update)

        await self.notify(update)

    async def produce_vfs_struct(self, ctx=None):
        config_reader = TgmountConfigReader()

        for (path, keys, vfs_config, ctx) in config_reader.walk_config_with_ctx(
            self._dir_config,
            resources=self._resources,
            ctx=none_fallback(ctx, CreateRootContext.from_resources(self._resources)),
        ):
            self._logger.info(f"produce_vfs_struct: {path}")

            sub_vfs_struct_producer = vfs_config.vfs_producer.from_config(
                self,
                self._resources,
                vfs_config,
                vfs_config.vfs_producer_arg,
            )

            self._by_path_producers[path] = sub_vfs_struct_producer
            self._by_producer_path[sub_vfs_struct_producer] = path

            await sub_vfs_struct_producer.produce_vfs_struct()

            self.wrappers[path] = vfs_config.vfs_wrappers
            # for w in vfs_config.vfs_wrappers:
            #     self._logger.info(f"Wrapping at {path}")
            #     _vfs_structure = await w.wrap_vfs_structure(_vfs_structure)
            # await self._vfs_structure.put(path, _vfs_structure)

    @staticmethod
    def from_config(
        resources: CreateRootResources, dir_config: TgmountRootSource
    ) -> "VfsStructureFromConfigProducer":
        return VfsStructureFromConfigProducer(
            dir_config=dir_config, resources=resources
        )
