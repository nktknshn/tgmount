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

from telethon import events, types
from telethon.client.telegrambaseclient import abc
from telethon.tl.custom import Message
from .logger import logger
from .client import TgmountTelegramClient
from tgmount.util import sets_difference

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
        client: TgmountTelegramClient,
        chat_id: str | int,
        limit: Optional[int],
    ) -> None:
        self._client = client
        self._chat_id = chat_id
        self._limit = limit

        self._messages: Optional[list[Message]] = None

        self._client.on(events.NewMessage(chats=chat_id))(self._on_new_message)
        self._client.on(events.MessageDeleted(chats=chat_id))(self._on_delete_message)

        self._listeners: list[Listener] = []

    async def _on_new_message(self, event: events.NewMessage.Event):
        if self._messages is None:
            self._messages = []

        self._messages.append(event.message)

        logger.info(f"New message: {event.message}")

        await self.notify(self._messages[:])

    async def _on_delete_message(self, event: events.MessageDeleted.Event):
        if self._messages is None:
            self._messages = []

        _msgs = []

        for m in self._messages:
            try:
                event.deleted_ids.index(m.id)
            except ValueError:
                _msgs.append(m)
            else:
                pass

        self._messages = _msgs

        await self.notify(self._messages[:])

    async def get_messages(self) -> list[Message]:
        if self._messages is not None:
            return self._messages[:]

        logger.info(f"Fetching {self._limit} messages from {self._chat_id}")

        self._messages = await self._client.get_messages_typed(
            self._chat_id,
            limit=self._limit,
        )

        return self._messages[:]

    def unsubscribe(self, listener: Listener[Arg]):
        self._listeners.remove(listener)

    @staticmethod
    def from_messages(ms: list[Message]) -> "MessageSourceProto":
        class TelegramMessageSource(MessageSourceProto):
            async def get_messages(self) -> frozenset[Message]:
                return frozenset(ms)

        return TelegramMessageSource()


class TelegramMessageSourceSimple(MessageSourceSubscribable):
    def __init__(self, messages=None) -> None:
        super().__init__()
        self._messages: Optional[MessagesSet] = messages
        self._logger = logger

    async def get_messages(self) -> MessagesSet:
        if self._messages is None:
            self._logger.error(f"Messages are not initiated yet")
            return Set()

        return self._messages

    async def set_messages(self, messages: MessagesSet):
        if self._messages is None:
            self._messages = messages

        removed, new, common = sets_difference(self._messages, messages)  # type: ignore

        if len(removed) > 0 or len(new) > 0:
            self._messages = messages

            await self.notify(self._messages)
