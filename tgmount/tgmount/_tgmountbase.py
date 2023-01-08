import os
from typing import Mapping, Optional, Type

from tgmount import fs, main, tgclient, tglog, vfs
from tgmount.fs.update import FileSystemOperationsUpdate
from tgmount.tgclient.add_hash import add_hash_to_telegram_message_class
from tgmount.tgclient.client_types import TgmountTelegramClientReaderProto
from tgmount.tgclient.message_source_simple import MessageSourceSimple
from tgmount.tgclient.telegram_message_source import (
    TelegramEventsDispatcher,
    TelegramMessagesFetcher,
)
from tgmount.tgmount.types import Set
from .vfs_tree_types import (
    TreeEventRemovedItems,
    TreeEventNewItems,
    TreeEventRemovedDirs,
    TreeEventNewDirs,
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
from tgmount import config

add_hash_to_telegram_message_class()


class TgmountBase:
    """
    Wraps the application state and all the async initialization, connects all the app parts together

    Connects VfsTree and FilesystemOperations by dispatches events from the virtual tree to FilesystemOperations
    """

    FileSystemOperations: Type[
        fs.FileSystemOperationsUpdatable
    ] = fs.FileSystemOperationsUpdatable

    VfsTreeProducer = VfsTreeProducer

    logger = tglog.getLogger("TgmountBase")

    def __init__(
        self,
        *,
        client: tgclient.client_types.TgmountTelegramClientReaderProto,
        resources: TgmountResources,
        root_config: Mapping,
        mount_dir: Optional[str] = None,
    ) -> None:
        self._client = client
        self._root_config = root_config
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

        self._events_dispatcher = TelegramEventsDispatcher(client)

    @property
    def client(self):
        return self._client

    @property
    def fs(self) -> fs.FileSystemOperationsUpdatable | None:
        return self._fs

    @property
    def vfs_tree(self) -> VfsTree:
        return self._vfs_tree

    async def register_sources_updates(self):
        """Add sources to the events dispatcher"""
        assert self._resources.fetchers_dict
        self.logger.debug(f"register_sources_updates()")

        # self.logger.info(self._resources.fetchers_dict)

        for k, fetcher_dict in self._resources.fetchers_dict.items():
            fetcher: TelegramMessagesFetcher = fetcher_dict["fetcher"]
            fetcher_cfg: config.MessageSource = fetcher_dict["config"]
            updates: bool = fetcher_dict["updates"]
            source: MessageSourceSimple = fetcher_dict["source"]

            if not updates:
                continue

            self.logger.debug(f"register_source({fetcher_cfg.entity})")

            self._events_dispatcher.connect(fetcher_cfg.entity, source)

    async def fetch_messages(self):
        """Fetch initial messages from message_sources"""
        assert self._resources.fetchers_dict

        self.logger.info(
            f"Fetching initial messages from {len(self._resources.fetchers_dict)} fetchers ({list(self._resources.fetchers_dict.keys())})..."
        )

        for k, fetcher_dict in self._resources.fetchers_dict.items():
            self.logger.info(f"Fetching from '{k}'...")

            fetcher: TelegramMessagesFetcher = fetcher_dict["fetcher"]
            source: MessageSourceSimple = fetcher_dict["source"]

            initial_messages = await fetcher.fetch()

            self.logger.info(f"Fetched {len(initial_messages)} messages.")

            await source.set_messages(Set(initial_messages), notify=False)

        # for entity_id, source in self._source_provider.as_mapping().items():
        #     self._messages_dispatcher.register_source(source)

        self.logger.info(f"Done fetching.")

    async def mount(
        self,
        *,
        mount_dir: Optional[str] = None,
        debug_fuse=False,
        min_tasks=10,
    ):
        """Mount process consists of two phases:"""
        mount_dir = none_fallback(mount_dir, self._mount_dir)

        if mount_dir is None:
            raise TgmountError(f"Missing mount destination.")

        self.logger.info(f"Building root...")

        assert self._events_dispatcher.is_paused

        # subscribe for updates from the messages sources
        await self.register_sources_updates()

        # fetch initial messages
        await self.fetch_messages()

        # create
        await self.create_fs()

        await self._events_dispatcher.resume()

        self.logger.info(f"Mounting into {mount_dir}")

        await main.util.mount_ops(
            self._fs,
            mount_dir=mount_dir,
            min_tasks=min_tasks,
            debug=debug_fuse,
        )

    # @measure_time(logger_func=logger.info)
    async def _update_fs(self, fs_update: FileSystemOperationsUpdate):

        if self._fs is None:
            self.logger.error(f"self._fs is not created yet.")
            return

        async with self._fs._update_lock:
            await self._fs.update(fs_update)

    async def produce_vfs_tree(self):
        self.logger.info(f"Producing VfsTree.")
        await self._producer.produce(self._vfs_tree, self._root_config)

    async def create_fs(self):
        """Produce VfsTree"""
        # for k, v in self._resources.sources.as_mapping().items():
        #     v.subscribe_to_client()

        async with self._source_provider.update_lock:
            await self.produce_vfs_tree()

            root_contet = await self._vfs_tree.get_dir_content()

            root = vfs.root(root_contet)

            self.logger.debug(f"Used loggers: {tglog.get_loggers()}")

            self._fs = self.FileSystemOperations(root)

    async def _on_vfs_tree_update(self, provider, source, updates: list[TreeEventType]):

        if len(updates) == 0:
            return

        fs_update = await self._join_tree_events(updates)

        self.logger.info(
            f"UPDATE: new_files={list(fs_update.new_files.keys())} removed_files={list(fs_update.removed_files)} update_dir_content={list(fs_update.update_dir_content.keys())} new_dir_content={list(fs_update.new_dirs.keys())} removed_dirs={fs_update.removed_dir_contents}"
        )

        await self._update_fs(fs_update)

    async def _join_tree_events(self, events: list[TreeEventType]):

        update = fs.FileSystemOperationsUpdate()

        for e in events:
            path = e.update_path

            if isinstance(e, TreeEventRemovedItems):
                for item in e.removed_items:
                    update.removed_files.append(os.path.join(path, item.name))
            elif isinstance(e, TreeEventNewItems):
                for item in e.new_items:
                    if isinstance(item, vfs.FileLike):
                        update.new_files[os.path.join(path, item.name)] = item
                    else:
                        update.new_dirs[os.path.join(path, item.name)] = item
                        # raise TgmountError(f"item is supposed to be FileLike")
            elif isinstance(e, TreeEventRemovedDirs):
                for path in e.removed_dirs:
                    update.removed_dir_contents.append(path)
            elif isinstance(e, TreeEventNewDirs):
                for path in e.new_dirs:
                    update.new_dirs[path] = await self._vfs_tree.get_dir_content(path)

        return update
