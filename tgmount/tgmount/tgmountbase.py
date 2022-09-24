import os
from typing import Any, Optional, Type, TypeGuard


from tgmount import config, fs, main, tg_vfs, tgclient, tglog, vfs
from tgmount.fs.util import measure_time
from tgmount.tgclient.message_source import (
    MessageSourceProto,
    MessageSourceProto,
)
from tgmount.tgmount.vfs_tree import (
    UpdateNewDirs,
    UpdateNewItems,
    UpdateRemovedDirs,
    UpdateRemovedItems,
    UpdateType,
)
from tgmount.tgmount.vfs_tree_producer import (
    SourcesProviderAccumulating,
    VfsTree,
    VfsTreeProducer,
)


from .error import TgmountError
from .types import CreateRootResources
from tgmount.tgclient.add_hash import add_hash

add_hash()

from telethon.tl.custom import Message


class Tgmount:
    FileSystemOperations: Type[
        fs.FileSystemOperationsUpdatable
    ] = fs.FileSystemOperationsUpdatable

    logger = tglog.getLogger("TgmountRootProducer")

    def __init__(
        self,
        *,
        client: tgclient.TgmountTelegramClient,
        root: dict,
        resources: CreateRootResources,
        mount_dir: Optional[str] = None,
    ) -> None:
        # self._client
        self._client = client
        self._mount_dir: Optional[str] = mount_dir

        self._root = root

        self._fs = None

        self._updates_pending = False
        self._is_building_root = False

        self._resources = resources
        # logger.setLevel(logging.ERROR)

    @property
    def client(self):
        return self._client

    # @property
    # def caches(self):
    #     return self._caches

    @property
    def fs(self) -> fs.FileSystemOperationsUpdatable | None:
        return self._fs

    # @measure_time(logger_func=logger.info)
    async def build_root(self) -> vfs.VfsRoot:
        tree = VfsTree()
        source_provider = SourcesProviderAccumulating(
            tree=tree, source_map=self._resources.sources.as_mapping()
        )

        # @measure_time(logger_func=Tgmount.logger.info)
        async def on_update(provider, source, updates: list[UpdateType]):
            update = fs.FileSystemOperationsUpdate()

            if len(updates) == 0:
                return

            for u in updates:
                path = u.update_path

                if isinstance(u, UpdateRemovedItems):
                    for item in u.removed_items:
                        update.removed_files.append(os.path.join(path, item.name))
                elif isinstance(u, UpdateNewItems):
                    for item in u.new_items:
                        update.new_files[os.path.join(path, item.name)] = item
                elif isinstance(u, UpdateRemovedDirs):
                    for path in u.removed_dirs:
                        update.removed_dir_contents.append(path)
                elif isinstance(u, UpdateNewDirs):
                    for path in u.new_dirs:
                        update.new_dirs[path] = await tree.get_dir_content(path)

            self.logger.info(
                f"UPDATE: new_files={list(update.new_files.keys())} removed_files={list(update.removed_files)} update_dir_content={list(update.update_dir_content.keys())} new_dir_content={list(update.new_dirs.keys())} removed_dirs={update.removed_dir_contents}"
            )

            if self._fs is None:
                self.logger.error(f"self._fs is not created yet.")
                return

            async with self._fs._update_lock:
                await self._fs.on_update(update)

        source_provider.updates.subscribe(on_update)

        tree_producer = VfsTreeProducer(
            resources=self._resources.set_sources(source_provider)
        )

        await tree_producer.produce(tree, self._root)

        return vfs.root(await tree.get_dir_content())

    async def create_fs(self):
        self.logger.info(f"Building root...")

        root = await self.build_root()

        self._fs = self.FileSystemOperations(root)

    async def mount(
        self,
        *,
        destination: Optional[str] = None,
        debug_fuse=False,
        min_tasks=10,
    ):
        await self.create_fs()

        mount_dir = destination if destination is not None else self._mount_dir

        if mount_dir is None:
            raise TgmountError(f"missing destination")

        # main.cleanup = self._fs.invalidate_all

        self.logger.info(f"Mounting into {mount_dir}")
        await main.util.mount_ops(
            self._fs,
            mount_dir=mount_dir,
            min_tasks=min_tasks,
            debug=debug_fuse,
        )
