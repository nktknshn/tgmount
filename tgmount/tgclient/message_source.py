from typing import Callable, Generic, Iterable, TypeVar
from tgmount.common.filter import FilterAllMessagesProto, FilterSingleMessage
from tgmount.tgclient.messages_collection import MessagesCollection, WithId, message_ids

from tgmount.util import none_fallback

from .logger import logger as _logger
from .message_source_types import MessageSourceProto, Subscribable

M = TypeVar("M", bound=WithId)

MessageSourceFilter = FilterSingleMessage[M] | FilterAllMessagesProto[M]


class MessageSource(MessageSourceProto, Generic[M]):
    """

    Generic storage for a set of messages. It's a proxy between telegram client and its users. It gets updated with methods and can be subscribed for new and for removed messages.

    The only constraint on message type is that it has to be hashable.

    Returns the stored messages set via `get_messages()` method.

    The updating methods are `add_messages(Set[M])`, `remove_messages(Set[M])`, `set_messages(Set[M])`. Calling these methods triggers `event_new_messages` or/and `event_removed_messages` events.

    `filters` property is a list of predicates that are applied to the incoming sets of messages. To add a filter use `add_filter`
    """

    logger = _logger.getChild("MessageSource")

    def __repr__(self) -> str:
        return f"MessageSource({self.tag})"

    def __init__(self, messages: Iterable[M] | None = None, tag=None) -> None:
        self._tag = none_fallback(tag, "NoTag")

        self._logger = self.logger.getChild(f"{self.tag}", suffix_as_tag=True)

        self._messages: MessagesCollection[M] | None = (
            MessagesCollection.from_iterable(messages) if messages is not None else None
        )

        self._filters: list[MessageSourceFilter[M]] = []

        self.event_new_messages: Subscribable = Subscribable()
        self.event_removed_messages: Subscribable = Subscribable()
        self.event_edited_messages: Subscribable = Subscribable()

    @property
    def tag(self):
        return self._tag

    @property
    def filters(self):
        return self._filters

    def add_filter(self, filt: MessageSourceFilter[M]):
        self._filters.append(filt)

    async def _filter_messages(self, messages: Iterable[M]) -> list[M]:
        res = list(messages)

        for f in self._filters:
            if FilterAllMessagesProto.guard(f):
                res = await f.filter(res)
            elif isinstance(f, Callable):
                res = list(filter(f, res))

        return res

    async def edit_messages(self, messages: Iterable[M]):

        if self._messages is None:
            self._logger.error(f"edit_messages(). Messages are not initiated yet")
            return

        filtered = await self._filter_messages(messages)

        old_messages = self._messages.get_by_ids([m.id for m in filtered])

        if old_messages is None:
            self._logger.error(
                f"edit_messages({messages}) Some of the edited messages has not been found in the message source"
            )
            return

        self._messages.add_messages(filtered, overwright=True)

        await self.event_edited_messages.notify(old_messages, filtered)

    async def add_messages(self, messages: Iterable[M]):

        if self._messages is None:
            self._messages = MessagesCollection()

        _filtered = await self._filter_messages(messages)

        self._logger.debug(f"add_messages({message_ids(_filtered)})")

        if len(_filtered) == 0:
            return

        diff = self._messages.add_messages(_filtered)

        if len(diff) == 0:
            return

        await self.event_new_messages.notify(diff)

    async def remove_messages(self, removed_messages: list[M]):
        if self._messages is None:
            self._messages = MessagesCollection()

        self._logger.debug(f"remove_messages({message_ids(removed_messages)})")

        if len(removed_messages) == 0:
            return

        inter = self._messages.remove_messages(removed_messages)

        await self.event_removed_messages.notify(inter)

    async def remove_messages_ids(self, removed_messages: list[int]):
        if self._messages is None:
            self._messages = MessagesCollection()

        self._logger.debug(f"remove_messages({removed_messages})")

        inter = self._messages.remove_ids(removed_messages)

        await self.event_removed_messages.notify(inter)

    async def get_by_ids(self, ids: list[int]) -> list[M] | None:
        if self._messages is None:
            self._logger.error(f"Messages are not initiated yet")
            return None

        return self._messages.get_by_ids(ids)

    async def get_messages(self) -> list[M]:
        if self._messages is None:
            self._logger.trace(f"get_messages()")
            self._logger.error(f"Messages are not initiated yet")
            return []

        messages = self._messages.get_messages_list()

        self._logger.trace(f"get_messages(). Returning {len(messages)} messages.")

        return messages

    async def set_messages(self, messages: list[M], notify=True):
        """Sets the source messages. `notify` sets if the subscribers should be notified about the update"""

        # if len(messages) == 0:
        #     self._logger.trace(f"empty set_messages request")
        #     return
        if len(messages) > 0:
            self._logger.debug(
                f"set_messages({len(messages)} messages, notify={notify})"
            )

        filtered = await self._filter_messages(messages)

        if self._messages is None:

            self._messages = MessagesCollection.from_iterable(filtered)

            if not notify:
                return

            await self.event_new_messages.notify(filtered)
            return

        removed, new, common = self._messages.get_difference(filtered)  # type: ignore

        # self._logger.debug(f"removed({removed}, new={new}, common={common})")

        if len(removed) > 0 or len(new) > 0:
            self._messages = MessagesCollection.from_iterable(messages)

            if not notify:
                return

            if len(new) > 0:
                await self.event_new_messages.notify(new)

            if len(removed) > 0:
                await self.event_removed_messages.notify(removed)
            # await self.notify(self._messages)
