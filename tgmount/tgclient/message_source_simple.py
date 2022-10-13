from abc import abstractmethod
from typing import (
    Any,
    Awaitable,
    Callable,
    Generic,
    Iterable,
    Optional,
    Protocol,
    TypeVar,
)

from telethon import events
from telethon.tl.custom import Message

from tgmount import tglog
from tgmount.tgclient.client_types import (
    TgmountTelegramClientEventProto,
    TgmountTelegramClientReaderProto,
)
from tgmount.util import none_fallback, sets_difference
from tgmount.tgmount.types import Set, MessagesSet
from .client import TgmountTelegramClient

from .message_source_types import MessageSourceSubscribableProto, Subscribable

M = TypeVar("M")

MessageSourceSimpleFilter = Callable[[M], bool]


class MessageSourceSimple(MessageSourceSubscribableProto, Generic[M]):
    def __init__(self, messages=None) -> None:
        self._logger = tglog.getLogger("MessageSourceSimple")
        self._messages: Optional[Set[M]] = messages

        self._filters: list[MessageSourceSimpleFilter[M]] = []

        self.event_new_messages: Subscribable = Subscribable()
        self.event_removed_messages: Subscribable = Subscribable()

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

        removed, new, common = sets_difference(self._messages, messages)  # type: ignore

        if len(removed) > 0 or len(new) > 0:
            self._messages = messages

            if not notify:
                return

            if len(new) > 0:
                await self.event_new_messages.notify(new)

            if len(removed) > 0:
                await self.event_removed_messages.notify(removed)
            # await self.notify(self._messages)
