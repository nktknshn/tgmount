from typing import Callable, Generic, Iterable, Optional, TypeVar

from tgmount import tglog
from tgmount.tgmount.types import Set
from tgmount.util import none_fallback, sets_difference

from .message_source_types import MessageSourceSubscribableProto, Subscribable

M = TypeVar("M")

MessageSourceSimpleFilter = Callable[[M], bool]


class MessageSourceSimple(MessageSourceSubscribableProto, Generic[M]):
    logger = tglog.getLogger("MessageSourceSimple")

    def __repr__(self) -> str:
        return f"MessageSourceSimple({self.tag})"

    def __init__(self, messages=None, tag=None) -> None:
        self._tag = tag

        self._logger = self.logger.getChild(f"{self.tag}")

        self._messages: Optional[Set[M]] = messages

        self._filters: list[MessageSourceSimpleFilter[M]] = []

        self.event_new_messages: Subscribable = Subscribable()
        self.event_removed_messages: Subscribable = Subscribable()

    @property
    def tag(self):
        return none_fallback(self._tag, "NoTag")

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

        if len(_set) == 0:
            return

        diff = _set.difference(self._messages)

        if len(diff) == 0:
            return

        self._messages |= diff

        await self.event_new_messages.notify(diff)

    async def remove_messages(self, messages: Iterable[M]):
        if self._messages is None:
            self._messages = Set()

        _set = Set(messages)
        inter = self._messages.intersection(_set)

        self._messages -= inter

        await self.event_removed_messages.notify(inter)

    async def get_messages(self) -> Set[M]:
        if self._messages is None:
            self._logger.error(f"Messages are not initiated yet")
            return Set()

        return self._messages

    async def set_messages(self, messages: Set[M], notify=True):
        _set = Set(await self._filter_messages(messages))

        if self._messages is None:
            self._messages = _set
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
