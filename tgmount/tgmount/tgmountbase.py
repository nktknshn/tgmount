import os
from typing import Mapping, Optional, Type

from tgmount import fs, main, tgclient, tglog, vfs
from tgmount.fs.update import FileSystemOperationsUpdate
from tgmount.tgclient.add_hash import add_hash_to_telegram_message_class
from .vfs_tree_types import (
    EventRemovedItems,
    EventNewItems,
    EventRemovedDirs,
    EventNewDirs,
    TreeEventType,
)
from tgmount.tgmount.vfs_tree_producer import (
    VfsTree,
    VfsTreeProducer,
)
from .vfs_tree_message_source import SourcesProviderAccumulating
from .error import TgmountError
from .tgmount_types import TgmountResources
from tgmount.util import none_fallback

add_hash_to_telegram_message_class()


class TgmountBase:
    FileSystemOperations: Type[
        fs.FileSystemOperationsUpdatable
    ] = fs.FileSystemOperationsUpdatable

    VfsTreeProducer = VfsTreeProducer

    _logger = tglog.getLogger("TgmountBase")

    def __init__(
        self,
        *,
        client: tgclient.client_types.TgmountTelegramClientReaderProto,
        root: Mapping,
        resources: TgmountResources,
        mount_dir: Optional[str] = None,
    ) -> None:
        self._client = client
        self._root = root
        self._resources = resources
        self._mount_dir: Optional[str] = mount_dir

        self._fs = None

        self._vfs_tree = VfsTree()

        self._source_provider = SourcesProviderAccumulating.from_sources_provider(
            self._resources.sources, self._vfs_tree
        )

        self._source_provider.accumulated_updates.subscribe(self._on_vfs_tree_update)

        self._producer = self.VfsTreeProducer(
            resources=self._resources.set_sources(self._source_provider)
        )

    @property
    def client(self):
        return self._client

    @property
    def fs(self) -> fs.FileSystemOperationsUpdatable | None:
        return self._fs

    @property
    def vfs_tree(self) -> VfsTree:
        return self._vfs_tree

    async def mount(
        self,
        *,
        mount_dir: Optional[str] = None,
        debug_fuse=False,
        min_tasks=10,
    ):

        mount_dir = none_fallback(mount_dir, self._mount_dir)

        if mount_dir is None:
            raise TgmountError(f"missing destination")

        self._logger.info(f"Building root...")

        await self.create_fs()

        self._logger.info(f"Mounting into {mount_dir}")

        await main.util.mount_ops(
            self._fs,
            mount_dir=mount_dir,
            min_tasks=min_tasks,
            debug=debug_fuse,
        )

    async def _join_events(self, events: list[TreeEventType]):

        update = fs.FileSystemOperationsUpdate()

        for e in events:
            path = e.update_path

            if isinstance(e, EventRemovedItems):
                for item in e.removed_items:
                    update.removed_files.append(os.path.join(path, item.name))
            elif isinstance(e, EventNewItems):
                for item in e.new_items:
                    if isinstance(item, vfs.FileLike):
                        update.new_files[os.path.join(path, item.name)] = item
                    else:
                        update.new_dirs[os.path.join(path, item.name)] = item
                        # raise TgmountError(f"item is supposed to be FileLike")
            elif isinstance(e, EventRemovedDirs):
                for path in e.removed_dirs:
                    update.removed_dir_contents.append(path)
            elif isinstance(e, EventNewDirs):
                for path in e.new_dirs:
                    update.new_dirs[path] = await self._vfs_tree.get_dir_content(path)

        return update

    # @measure_time(logger_func=logger.info)
    async def _update_fs(self, fs_update: FileSystemOperationsUpdate):

        if self._fs is None:
            self._logger.error(f"self._fs is not created yet.")
            return

        async with self._fs._update_lock:
            await self._fs.update(fs_update)

    async def produce_vfs_tree(self):
        await self._producer.produce(self._vfs_tree, self._root)

    async def create_fs(self):

        # for k, v in self._resources.sources.as_mapping().items():
        #     v.subscribe_to_client()

        await self.produce_vfs_tree()

        root_contet = await self._vfs_tree.get_dir_content()

        root = vfs.root(root_contet)

        self._fs = self.FileSystemOperations(root)

    async def _on_vfs_tree_update(self, provider, source, updates: list[TreeEventType]):

        if len(updates) == 0:
            return

        fs_update = await self._join_events(updates)

        self._logger.info(
            f"UPDATE: new_files={list(fs_update.new_files.keys())} removed_files={list(fs_update.removed_files)} update_dir_content={list(fs_update.update_dir_content.keys())} new_dir_content={list(fs_update.new_dirs.keys())} removed_dirs={fs_update.removed_dir_contents}"
        )

        await self._update_fs(fs_update)
