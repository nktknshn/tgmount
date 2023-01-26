import logging
import os
from typing import Mapping, Optional, Type

from telethon import events
from tests import tgmount

from tgmount import fs, main, tgclient, tglog, vfs
from tgmount.fs.update import FileSystemOperationsUpdate
from tgmount.tgclient.add_hash import add_hash_to_telegram_message_class
from tgmount.tgclient.message_source import MessageSource
from tgmount.tgclient.events_disptacher import EntityId, TelegramEventsDispatcher
from tgmount.tgmount.producers.producer_plain import VfsTreeProducerPlainDir
from tgmount.tgmount.vfs_tree_producer import VfsTree, VfsTreeProducer
from tgmount.util import measure_time, none_fallback
from tgmount.vfs.util import MyLock

from .error import TgmountError
from .logger import logger as _logger
from .tgmount_types import TgmountResources
from .vfs_tree import TreeListener, VfsTreeDir
from .vfs_tree_types import (
    TreeEventNewDirs,
    TreeEventNewItems,
    TreeEventRemovedDirs,
    TreeEventRemovedItems,
    TreeEventType,
    TreeEventUpdatedItems,
)

# add_hash_to_telegram_message_class()

# VfsTreeProducerPlainDir.logger.setLevel(logging.CRITICAL)

from tgmount import tgmount

# tgmount.producers.logger.setLevel(logging.DEBUG)


class TgmountBase:
    """
    Wraps the application state and all the async initialization, connects all the app parts together

    Connects VfsTree and FilesystemOperations by dispatching events from the virtual tree to FilesystemOperations
    """

    FileSystemOperations: Type[
        fs.FileSystemOperationsUpdatable
    ] = fs.FileSystemOperationsUpdatable

    logger = _logger.getChild("TgmountBase")

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

        self._vfs_tree: VfsTree
        self._producer: VfsTreeProducer
        self._events_dispatcher: TelegramEventsDispatcher
        self._update_lock = MyLock("TgmountBase._update_lock", self.logger)

    @property
    def vfs_tree(self) -> VfsTree:
        return self._vfs_tree

    @vfs_tree.setter
    def vfs_tree(self, vfs_tree: VfsTree):
        self._vfs_tree = vfs_tree

    @property
    def resources(self) -> TgmountResources:
        return self._resources

    @property
    def events_dispatcher(self) -> TelegramEventsDispatcher:
        return self._events_dispatcher

    @events_dispatcher.setter
    def events_dispatcher(self, ed: TelegramEventsDispatcher):
        self._events_dispatcher = ed

    @property
    def producer(self) -> VfsTreeProducer:
        return self._producer

    @producer.setter
    def producer(self, producer: VfsTreeProducer):
        self._producer = producer

    @property
    def client(self):
        return self._client

    @property
    def fs(self) -> fs.FileSystemOperationsUpdatable | None:
        return self._fs

    async def fetch_messages(self):
        """Fetch initial messages from message_sources"""
        # assert self._resources.fetchers_dict

        self.logger.info(
            f"Fetching initial messages from ({list(self._resources.fetchers_dict.keys())})..."
        )

        for k, fetcher in self._resources.fetchers_dict.items():
            self.logger.info(f"Fetching from '{k}'...")
            source: MessageSource | None = self._resources.sources.get(k)

            assert source

            initial_messages = await fetcher.fetch()

            self.logger.info(f"Fetched {len(initial_messages)} messages.")

            await source.set_messages(initial_messages, notify=False)

        self.logger.info(f"Done fetching.")

    """ 
    New way:
        0. TgmountBase subscribeb to client updates
        1. Telegram receives update
        - Update lock here
        2. Update goes into the dispatcher
        3. Disptacher if not paused (it is paused during initial messages fetching) passes update into the message source
        4. Message source passes update to the subscribed producers
        5. Producers update the VfsTree
        6. VfsTree generates events
        7. TgmountBase receives them turning into FileOperations update and passing to it
        - Unlock here
    """

    @measure_time(logger_func=logger.info)
    async def on_new_message(self, entity_id: EntityId, event: events.NewMessage.Event):
        self.logger.info(f"on_new_message({event})")

        listener = TreeListener(self._vfs_tree)

        async with self._update_lock:

            async with listener:
                await self.events_dispatcher.process_new_message_event(entity_id, event)

            if len(listener.events) > 0:
                self.logger.debug(f"Tree generated {len(listener.events)} events")
                await self._on_vfs_tree_update(listener.events)

        self.logger.info(f"on_new_message() done")

    @measure_time(logger_func=logger.info)
    async def on_delete_message(
        self, entity_id: EntityId, event: events.MessageDeleted.Event
    ):
        self.logger.info(f"on_delete_message({event})")
        listener = TreeListener(self._vfs_tree)

        async with self._update_lock:
            async with listener:
                await self.events_dispatcher.process_delete_message_event(
                    entity_id, event
                )

            if len(listener.events) > 0:
                self.logger.debug(f"Tree generated {len(listener.events)} events")
                await self._on_vfs_tree_update(listener.events)

        self.logger.info(f"on_delete_message() done")

    @measure_time(logger_func=logger.info)
    async def on_edited_message(
        self, entity_id: EntityId, event: events.MessageEdited.Event
    ):
        self.logger.info(f"on_edited_message({event})")

        listener = TreeListener(self._vfs_tree)

        async with self._update_lock:
            async with listener:
                await self.events_dispatcher.process_edited_message_event(
                    entity_id, event
                )

            if len(listener.events) > 0:
                self.logger.debug(f"Tree generated {len(listener.events)} events")
                await self._on_vfs_tree_update(listener.events)

        self.logger.info(f"on_delete_message() done")

    # @measure_time(logger_func=logger.info)
    async def _update_fs(self, fs_update: FileSystemOperationsUpdate):

        if self._fs is None:
            self.logger.error(f"self._fs is not created yet.")
            return

        async with self._fs._update_lock:
            await self._fs.update(fs_update)

    async def produce_vfs_tree(self):
        """Produce VfsTree"""

        self.logger.info(f"Producing VfsTree.")
        await self._producer.produce(self._vfs_tree, self._root_config)

    async def resume_dispatcher(self):
        await self.events_dispatcher.resume()

    async def create_fs(self):
        """Produce VfsTree and create `FileSystemOperations`"""

        await self.produce_vfs_tree()

        root_contet = await self._vfs_tree.get_dir_content()

        root = vfs.root(root_contet)

        self._fs = self.FileSystemOperations(root)

    async def _on_vfs_tree_update(self, updates: list[TreeEventType]):

        if len(updates) == 0:
            return

        fs_update = await self._join_tree_events(updates)

        self.logger.info(
            f"UPDATE: new_files={list(fs_update.new_files.keys())}"
            + f" removed_files={list(fs_update.removed_files)}"
            # + f" update_dir_content={list(fs_update.update_dir_content.keys())}"
            + f" new_dir_content={list(fs_update.new_dirs.keys())}"
            + f" removed_dirs={fs_update.removed_dirs}"
        )

        await self._update_fs(fs_update)

    async def _join_tree_events(self, events: list[TreeEventType[VfsTreeDir]]):

        update = fs.FileSystemOperationsUpdate()

        for e in events:
            if isinstance(e, TreeEventRemovedItems):
                path = e.sender.path

                for item in e.removed_items:
                    update.removed_files.append(os.path.join(path, item.name))

            elif isinstance(e, TreeEventNewItems):
                path = e.sender.path

                for item in e.new_items:
                    if isinstance(item, vfs.FileLike):
                        update.new_files[os.path.join(path, item.name)] = item
                    else:
                        update.new_dirs[os.path.join(path, item.name)] = item

            elif isinstance(e, TreeEventRemovedDirs):
                for path in e.removed_dirs:
                    update.removed_dirs.append(path)

            elif isinstance(e, TreeEventUpdatedItems):
                for path, item in e.updated_items.items():
                    update.update_items[path] = item

            elif isinstance(e, TreeEventNewDirs):
                for path in e.new_dirs:
                    update.new_dirs[path] = await self._vfs_tree.get_dir_content(path)

        return update

    async def mount(
        self,
        *,
        mount_dir: Optional[str] = None,
        debug_fuse=False,
        min_tasks=10,
    ):
        """Mount process consists of two phases: fetching messages and building vfs root"""
        mount_dir = none_fallback(mount_dir, self._mount_dir)

        if mount_dir is None:
            raise TgmountError(f"Missing mount destination.")

        self.logger.info(f"Building root...")

        assert self._events_dispatcher.is_paused

        # fetch initial messages
        await self.fetch_messages()

        # create
        await self.create_fs()

        # pass updates that has been received during previous stages
        await self._events_dispatcher.resume()

        self.logger.info(f"Mounting into {mount_dir}")

        await main.util.mount_ops(
            self._fs,
            mount_dir=mount_dir,
            min_tasks=min_tasks,
            debug=debug_fuse,
        )


class TgmountBaseMounter:
    def __init__(self) -> None:
        pass

    def mount(
        self,
        tgm: TgmountBase,
        *,
        mount_dir: Optional[str] = None,
        debug_fuse=False,
        min_tasks=10,
    ):
        pass
