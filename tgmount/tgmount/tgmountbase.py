import os
from typing import Mapping, Optional, Type

from tgmount import fs, main, tgclient, tglog, vfs
from tgmount.tgclient.add_hash import add_hash
from .vfs_tree_types import (
    UpdateRemovedItems,
    UpdateNewItems,
    UpdateRemovedDirs,
    UpdateNewDirs,
    UpdateType,
)
from tgmount.tgmount.vfs_tree_producer import (
    VfsTree,
    VfsTreeProducer,
)
from .vfs_tree_message_source import SourcesProviderAccumulating
from .error import TgmountError
from .tgmount_types import TgmountResources
from tgmount.util import none_fallback

add_hash()


class TgmountBase:
    FileSystemOperations: Type[
        fs.FileSystemOperationsUpdatable
    ] = fs.FileSystemOperationsUpdatable

    logger = tglog.getLogger("TgmountBase")

    def __init__(
        self,
        *,
        client: tgclient.TgmountTelegramClient,
        root: Mapping,
        resources: TgmountResources,
        mount_dir: Optional[str] = None,
    ) -> None:
        self._client = client
        self._root = root
        self._resources = resources
        self._mount_dir: Optional[str] = mount_dir

        self._fs = None

        self._updates_pending = False
        self._is_building_root = False

    @property
    def client(self):
        return self._client

    @property
    def fs(self) -> fs.FileSystemOperationsUpdatable | None:
        return self._fs

    async def mount(
        self,
        *,
        mount_dir: Optional[str] = None,
        debug_fuse=False,
        min_tasks=10,
    ):
        await self._create_fs()

        mount_dir = none_fallback(mount_dir, self._mount_dir)

        if mount_dir is None:
            raise TgmountError(f"missing destination")

        self.logger.info(f"Mounting into {mount_dir}")

        await main.util.mount_ops(
            self._fs,
            mount_dir=mount_dir,
            min_tasks=min_tasks,
            debug=debug_fuse,
        )

    async def _create_fs(self):
        self.logger.info(f"Building root...")

        root = await self._build_root()

        self._fs = self.FileSystemOperations(root)

    async def _join_updates(self, tree: VfsTree, updates: list[UpdateType]):

        update = fs.FileSystemOperationsUpdate()

        for u in updates:
            path = u.update_path

            if isinstance(u, UpdateRemovedItems):
                for item in u.removed_items:
                    update.removed_files.append(os.path.join(path, item.name))
            elif isinstance(u, UpdateNewItems):
                for item in u.new_items:
                    if isinstance(item, vfs.FileLike):
                        update.new_files[os.path.join(path, item.name)] = item
                    else:
                        raise TgmountError(f"item is supposed to be FileLike")
            elif isinstance(u, UpdateRemovedDirs):
                for path in u.removed_dirs:
                    update.removed_dir_contents.append(path)
            elif isinstance(u, UpdateNewDirs):
                for path in u.new_dirs:
                    update.new_dirs[path] = await tree.get_dir_content(path)

        return update

    # @measure_time(logger_func=logger.info)
    async def _build_root(self) -> vfs.VfsRoot:
        tree = VfsTree()

        # @measure_time(logger_func=Tgmount.logger.info)
        async def on_vfs_tree_update(provider, source, updates: list[UpdateType]):

            if len(updates) == 0:
                return

            update = await self._join_updates(tree, updates)

            self.logger.info(
                f"UPDATE: new_files={list(update.new_files.keys())} removed_files={list(update.removed_files)} update_dir_content={list(update.update_dir_content.keys())} new_dir_content={list(update.new_dirs.keys())} removed_dirs={update.removed_dir_contents}"
            )

            if self._fs is None:
                self.logger.error(f"self._fs is not created yet.")
                return

            async with self._fs._update_lock:
                await self._fs.on_update(update)

        source_provider = SourcesProviderAccumulating(
            tree=tree, source_map=self._resources.sources.as_mapping()
        )

        source_provider.updates.subscribe(on_vfs_tree_update)

        tree_producer = VfsTreeProducer(
            resources=self._resources.set_sources(source_provider)
        )

        await tree_producer.produce(tree, self._root)

        return vfs.root(await tree.get_dir_content())
