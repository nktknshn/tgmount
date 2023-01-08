from typing import Callable, Generic, Iterable, Optional, TypeVar

from tgmount import tglog
from tgmount.tgmount.types import Set
from tgmount.util import none_fallback, sets_difference

from .message_source_types import MessageSourceSubscribableProto, Subscribable

M = TypeVar("M")

MessageSourceSimpleFilter = Callable[[M], bool]


class MessageSourceSimple(MessageSourceSubscribableProto, Generic[M]):
    """

    Generic storage for a set of messages. It's a proxy between telegram client and its users. It gets updated with methods and can be subscribed for new and for removed messages.

    The only constraint on message type is that it has to be hashable.

    Returns the stored messages set via `get_messages()` method.

    The updating methods are `add_messages(Set[M])`, `remove_messages(Set[M])`, `set_messages(Set[M])`. Calling these methods triggers `event_new_messages` or/and `event_removed_messages` events.

    `filters` property is a list of predicates that are applied to the incoming sets of messages. To add a filter use `add_filter`
    """

    logger = tglog.getLogger("MessageSourceSimple")

    def __repr__(self) -> str:
        return f"MessageSourceSimple({self.tag})"

    def __init__(self, messages=None, tag=None) -> None:
        self._tag = none_fallback(tag, "NoTag")

        self._logger = self.logger.getChild(f"{self.tag}")

        self._messages: Optional[Set[M]] = messages
        self._filters: list[MessageSourceSimpleFilter[M]] = []

        self.event_new_messages: Subscribable = Subscribable()
        self.event_removed_messages: Subscribable = Subscribable()

    @property
    def tag(self):
        return self._tag

    @property
    def filters(self):
        return self._filters

    def add_filter(self, filt):
        self._filters.append(filt)

    async def _filter_messages(self, messages: Iterable[M]) -> list[M]:
        res = []

        for m in messages:
            for f in self._filters:
                if not f(m):
                    break
            else:
                res.append(m)

        return res

    async def add_messages(self, messages: Iterable[M]):

        if self._messages is None:
            self._messages = Set()

        _set = Set(await self._filter_messages(messages))

        self._logger.debug(f"add_messages({len(_set)})")

        if len(_set) == 0:
            return

        diff = _set.difference(self._messages)

        if len(diff) == 0:
            return

        self._messages |= diff

        await self.event_new_messages.notify(diff)

    # async def remove_messages_by_func(
    #     self, select_removed: Callable[[Iterable[M]], Iterable[M]]
    # ):
    #     msgs = await self.get_messages()

    async def remove_messages(self, messages: Iterable[M]):
        if self._messages is None:
            self._messages = Set()

        _set = Set(messages)

        self._logger.debug(f"remove_messages({len(_set)})")

        inter = self._messages.intersection(_set)

        self._messages -= inter

        await self.event_removed_messages.notify(inter)

    async def get_messages(self) -> Set[M]:
        self._logger.debug(f"get_messages()")

        if self._messages is None:
            self._logger.error(f"Messages are not initiated yet")
            return Set()

        return self._messages

    async def set_messages(self, messages: Set[M], notify=True):
        """Sets the source messages. `notify` controls if the subscribers should be notified about the update"""

        _set = Set(await self._filter_messages(messages))

        self._logger.debug(f"set_messages({len(_set)}, notify={notify})")

        if self._messages is None:
            self._messages = _set
            if not notify:
                return

            await self.event_new_messages.notify(_set)
            return

        removed, new, common = sets_difference(self._messages, _set)  # type: ignore

        if len(removed) > 0 or len(new) > 0:
            self._messages = messages

            if not notify:
                return

            if len(new) > 0:
                await self.event_new_messages.notify(new)

            if len(removed) > 0:
                await self.event_removed_messages.notify(removed)
            # await self.notify(self._messages)
