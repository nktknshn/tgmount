import logging
from typing import Mapping

from telethon.tl.custom import Message

from tgmount import tgclient, tglog
from tgmount.tgclient.message_source_types import (
    MessageSourceSubscribableProto,
    Subscribable,
)
from tgmount.tgmount.providers.provider_sources import (
    SourcesProvider,
    SourcesProviderProto,
)
from tgmount.tgmount.types import Set
from tgmount.tgmount.vfs_tree import VfsTree, VfsTreeDir
from tgmount.tgmount.vfs_tree_types import TreeEventType
from tgmount.vfs.util import MyLock
from tgmount.util import measure_time

""" 

TelegramMessageSource(MessageSourceSimple) receives updates
 
currently: 
TelegramClient -> TelegramMessageSource -> SourcesProviderMessageSource -> VfsTreeProducers -> VfsTree -> SourcesProviderMessageSource -> TgmountBase -> FileSystemOperationsUpdate

TelegramClient -> TelegramUpdatesDispatcher( ) -> SimpleMessageSource -> VfsTreeProducer -> VfsTree -> TelegramUpdatesDispatcher

TelegramClient -> TgmountBase().process_update() -> SimpleMessageSource -> VfsTreeProducer -> VfsTree -> TelegramUpdatesDispatcher

"""


class SourcesProviderMessageSource(
    Subscribable, tgclient.MessageSourceSubscribableProto
):
    """
    Wraps a MessageSourceSubscribableProto to accumulate updates in VfsTree
    that were triggered by the wrapped message source

    Acquires provider's update_lock when processing update. So the updates
    processing is atomic
    """

    logger = tglog.getLogger(f"AccumulatingMessageSource()")

    def __init__(
        self,
        provider: "SourcesProviderAccumulating",
        tree: VfsTree,
        wrapped_source: tgclient.MessageSourceSubscribableProto,
    ) -> None:
        Subscribable.__init__(self)

        self._provider = provider
        self._wrapped_source = wrapped_source
        self._tree = tree

        self._wrapped_source.event_removed_messages.subscribe(self.on_removed_messages)
        self._wrapped_source.event_new_messages.subscribe(self.on_new_message)

        """ Events for file system """
        self.accumulated_updates: Subscribable = Subscribable()

        """ Events for dependednt message sources """
        self.event_new_messages: Subscribable = Subscribable()

        """ Events for dependednt message sources """
        self.event_removed_messages: Subscribable = Subscribable()

        # self._lock = MyLock(
        #     f"SourcesProviderMessageSource.lock({self._wrapped_source})", self.logger
        # )

    async def get_messages(self) -> Set[Message]:
        return await self._wrapped_source.get_messages()

    @measure_time(logger_func=logger.info)
    async def on_new_message(self, source, messages: Set[Message]):
        self.logger.debug(f"update_new_message({len(messages)})")

        # start accumulating updates
        async with self._provider.update_lock:
            _events = []

            async def append_events(
                sender, events: list[TreeEventType], child: VfsTreeDir
            ):
                if events is None:
                    pass

                _events.extend(events)

            self._tree.subscribe(append_events)
            self.logger.info(f"Dispatching {len(messages)} messages to {self._tree}")

            await self.event_new_messages.notify(messages)

            self._tree.unsubscribe(append_events)
            self.logger.info(
                f"Done dispatching messages. Tree returned {len(_events)} events."
            )

            if len(_events) > 0:
                self.logger.info(f"Dispatching {len(_events)} events to subscribers")
                await self.accumulated_updates.notify(_events)
                self.logger.info(f"Done dispatching events")

    @measure_time(logger_func=logger.info)
    async def on_removed_messages(self, source, messages: Set[Message]):
        self.logger.debug("removed_messages()")
        async with self._provider.update_lock:
            _updates = []

            async def append_update(
                sender, updates: list[TreeEventType], child: VfsTreeDir
            ):
                _updates.extend(updates)

            self._tree.subscribe(append_update)
            await self.event_removed_messages.notify(messages)

            self._tree.unsubscribe(append_update)
            await self.accumulated_updates.notify(_updates)


class SourcesProviderAccumulating(SourcesProvider[SourcesProviderMessageSource]):
    """
    Wraps MessageSource to accumulate updates from the VfsTree that were
    triggered by parent message source. Subscribe to `accumulated_updates` for
    the list of updates
    """

    MessageSource = SourcesProviderMessageSource
    logger = tglog.getLogger("SourcesProviderAccumulating")
    # logger.setLevel(logging.DEBUG)

    def __init__(
        self,
        tree: VfsTree,
        source_map: Mapping[str, tgclient.MessageSourceSubscribableProto],
    ) -> None:

        self.accumulated_updates: Subscribable = Subscribable()
        self._tree = tree

        """Locks when new event (new messsage or removed messages) received until the event is processed by VfsTree and FileSystemOperations.update"""
        self._update_lock = MyLock(
            "SourcesProviderAccumulating.update_lock",
            logger=self.logger,
            level=logging.INFO,
        )

        super().__init__(
            {k: self.MessageSource(self, self._tree, v) for k, v in source_map.items()}
        )

        for k, v in self._source_map.items():
            v.accumulated_updates.subscribe(self.accumulated_updates.notify)

    @property
    def update_lock(self):
        """This lock is used to make VfsTree updates atomic"""
        return self._update_lock

    @classmethod
    def from_sources_provider(cls, provider: SourcesProviderProto, tree: VfsTree):
        return cls(tree, provider.as_mapping())
