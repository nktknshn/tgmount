from typing import Mapping

from telethon.tl.custom import Message

from tgmount import tgclient, tglog
from tgmount.tgclient.message_source import Subscribable
from tgmount.tgmount.providers.provider_sources import SourcesProvider
from tgmount.tgmount.vfs_tree import VfsTree
from tgmount.tgmount.vfs_tree_types import UpdateType


class SourcesProviderMessageSource(
    Subscribable, tgclient.MessageSourceSubscribableProto
):
    """
    Wraps MessageSource to accumulate updates in the tree that were triggered
    by parent message source
    """

    def __init__(
        self,
        tree: VfsTree,
        wrapped_source: tgclient.MessageSourceSubscribableProto,
    ) -> None:
        Subscribable.__init__(self)
        self._wrapped_source = wrapped_source
        self._tree = tree

        self._wrapped_source.event_removed_messages.subscribe(self.removed_messages)
        self._wrapped_source.event_new_messages.subscribe(self.update_new_message)

        """ Events for file system """
        self.accumulated_updates: Subscribable = Subscribable()

        """ Events for dependednt message sources """
        self.event_new_messages: Subscribable = Subscribable()

        """ Events for dependednt message sources """
        self.event_removed_messages: Subscribable = Subscribable()

        self._logger = tglog.getLogger(f"SourcesProviderMessageSource()")

    async def get_messages(self) -> list[Message]:
        return await self._wrapped_source.get_messages()

    async def update_new_message(self, source, messages: list[Message]):

        _updates = []

        async def append_update(source, updates: list[UpdateType]):
            _updates.extend(updates)

        # start accumulating updates
        self._tree.subscribe(append_update)
        await self.event_new_messages.notify(messages)
        self._tree.unsubscribe(append_update)

        await self.accumulated_updates.notify(_updates)

    async def removed_messages(self, source, messages: list[Message]):
        self._logger.debug("removed_messages")

        _updates = []

        async def append_update(source, updates: list[UpdateType]):
            _updates.extend(updates)

        self._tree.subscribe(append_update)
        await self.event_removed_messages.notify(messages)

        self._tree.unsubscribe(append_update)
        await self.accumulated_updates.notify(_updates)


class SourcesProviderAccumulating(SourcesProvider[SourcesProviderMessageSource]):
    """
    Wraps MessageSource to accumulate updates in the tree that were triggered
    by parent message source before passing them to FS
    """

    MessageSource = SourcesProviderMessageSource

    def __init__(
        self,
        tree: VfsTree,
        source_map: Mapping[str, tgclient.MessageSourceSubscribableProto],
    ) -> None:

        self.accumulated_updates: Subscribable = Subscribable()
        self._tree = tree

        super().__init__(
            {k: self.MessageSource(self._tree, v) for k, v in source_map.items()}
        )

        for k, v in self._source_map.items():
            v.accumulated_updates.subscribe(self.accumulated_updates.notify)
