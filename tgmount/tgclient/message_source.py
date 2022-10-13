from abc import abstractmethod
from typing import (
    Any,
    Awaitable,
    Callable,
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
from .client import TgmountTelegramClient
from .logger import logger

T = TypeVar("T")
Arg = TypeVar("Arg")

Set = frozenset
MessagesSet = frozenset[Message] | set[Message]

Listener = Callable[
    [
        Any,
        Arg,
    ],
    Awaitable[None],
]


class SubscribableProto(Protocol[Arg]):
    @abstractmethod
    def subscribe(self, listener: Listener[Arg]):
        ...

    @abstractmethod
    def unsubscribe(self, listener: Listener[Arg]):
        ...


class MessageSourceProto(Protocol):
    @abstractmethod
    async def get_messages(self) -> Set[Message]:
        pass


class MessageSourceSubscribableProto(
    MessageSourceProto, SubscribableProto[list[Message]]
):

    event_new_messages: SubscribableProto[list[Message]]
    event_removed_messages: SubscribableProto[list[Message]]

    @abstractmethod
    async def get_messages(self) -> list[Message]:
        ...

    @abstractmethod
    def subscribe(self, listener: Listener[list[Message]]):
        ...

    @abstractmethod
    def unsubscribe(self, listener: Listener[Arg]):
        ...


class Subscribable(SubscribableProto[Arg]):
    def __init__(self) -> None:
        self._listeners: list[Listener[Arg]] = []

    def subscribe(self, listener: Listener[Arg]):
        self._listeners.append(listener)

    def unsubscribe(self, listener: Listener[Arg]):
        self._listeners.remove(listener)

    async def notify(self, *args):
        for listener in self._listeners:
            await listener(self, *args)


class MessageSourceSubscribable(MessageSourceSubscribableProto):
    def __init__(self) -> None:
        self._listeners: list[Listener] = []

    def subscribe(self, listener: Listener):
        self._listeners.append(listener)

    async def notify(self, *args):
        for listener in self._listeners:
            await listener(self, *args)

    def unsubscribe(self, listener: Listener[Arg]):
        self._listeners.remove(listener)


class TelegramMessageSource(MessageSourceSubscribable):
    def __init__(
        self,
        client: TgmountTelegramClientReaderProto,
        chat_id: str | int,
        limit: Optional[int],
    ) -> None:
        self._client = client
        self._chat_id = chat_id
        self._limit = limit

        self._logger = tglog.getLogger(f"TelegramMessageSource({self._chat_id})")

        self._messages: Optional[list[Message]] = None

        self._listeners: list[Listener] = []

        self.event_new_messages: Subscribable = Subscribable()
        self.event_removed_messages: Subscribable = Subscribable()

        self._filters = []

        self.subscribe_to_client()

    def subscribe_to_client(self):
        self._logger.info(f"Subscribing to {self._client} updates.")

        # self._client.on(events.NewMessage(chats=self._chat_id))(self._on_new_message)
        # self._client.on(events.MessageDeleted(chats=self._chat_id))(
        #     self._on_delete_message
        # )
        self._client.subscribe_new_messages(self._on_new_message, chats=self._chat_id)
        self._client.subscribe_removed_messages(
            self._on_delete_message, chats=self._chat_id
        )

    @property
    def filters(self):
        return self._filters

    async def _on_new_message(self, event: events.NewMessage.Event):
        self._logger.debug(f"_on_new_message")

        if self._messages is None:
            self._messages = []

        for f in self._filters:
            if not f(event.message):
                self._logger.info(f"Filtered out message: {event.message}")
                return

        self._messages.append(event.message)

        self._logger.info(f"New message: {event.message}")

        await self.event_new_messages.notify([event.message])

        # await self.notify(self._messages[:])

    async def _on_delete_message(self, event: events.MessageDeleted.Event):
        self._logger.info(f"_on_delete_message({event.deleted_ids})")

        if self._messages is None:
            self._messages = []

        _msgs = []
        _removed = []

        for m in self._messages:
            try:
                event.deleted_ids.index(m.id)
            except ValueError:
                _msgs.append(m)
            else:
                _removed.append(m)

        self._messages = _msgs

        if len(_removed) > 0:
            await self.event_removed_messages.notify(_removed)
        else:
            self._logger.error(f"no messages removed: {event.deleted_ids}")
        # await self.notify(self._messages[:])

    async def get_messages(self) -> list[Message]:
        if self._messages is not None:
            return self._messages[:]

        self._logger.info(
            f"Fetching {none_fallback(self._limit, 'all')} messages from {self._chat_id}"
        )

        messages = await self._client.get_messages(self._chat_id, limit=self._limit)

        self._logger.info(f"Received {len(messages)}")

        self._messages = []

        for m in messages:
            for f in self._filters:
                if not f(m):
                    break
            else:
                self._messages.append(m)

        return self._messages[:]

    def unsubscribe(self, listener: Listener[Arg]):
        self._listeners.remove(listener)

    @staticmethod
    def from_messages(ms: list[Message]) -> "MessageSourceProto":
        class TelegramMessageSource(MessageSourceProto):
            async def get_messages(self) -> frozenset[Message]:
                return frozenset(ms)

        return TelegramMessageSource()


class MessageSourceSimple(MessageSourceSubscribable):
    def __init__(self, messages=None) -> None:
        super().__init__()
        self._messages: Optional[MessagesSet] = messages
        self._logger = logger

        self._filters = []

        self.event_new_messages: Subscribable = Subscribable()
        self.event_removed_messages: Subscribable = Subscribable()

    @property
    def filters(self):
        return self._filters

    def add_filter(self, filt):
        self._filters.append(filt)

    async def _filter_messages(self, messages: Iterable[Message]):
        res = []
        for m in messages:
            for f in self._filters:
                if not f(m):
                    break
            res.append(m)

        return res

    async def add_messages(self, messages: Iterable[Message]):
        if self._messages is None:
            self._messages = Set()

        self._messages |= Set(await self._filter_messages(messages))

        await self.event_new_messages.notify(messages)

    async def remove_messages(self, messages: list[Message]):
        if self._messages is None:
            self._messages = Set()

        self._messages -= Set(messages)

        await self.event_removed_messages.notify(messages)

    async def get_messages(self) -> MessagesSet:
        if self._messages is None:
            self._logger.error(f"Messages are not initiated yet")
            return Set()

        return self._messages

    async def set_messages(self, messages: MessagesSet):
        if self._messages is None:
            self._messages = Set(await self._filter_messages(messages))

        removed, new, common = sets_difference(self._messages, messages)  # type: ignore

        if len(removed) > 0 or len(new) > 0:
            self._messages = messages

            if len(new) > 0:
                await self.event_new_messages.notify(new)

            if len(removed) > 0:
                await self.event_removed_messages.notify(removed)
            # await self.notify(self._messages)
