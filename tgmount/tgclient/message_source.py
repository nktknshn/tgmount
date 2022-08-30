from abc import abstractmethod
from typing import (
    Awaitable,
    Callable,
    Iterable,
    Optional,
    Protocol,
)

from telethon import events, types
from telethon.client.telegrambaseclient import abc
from telethon.tl.custom import Message
from tgmount import tgclient
from .logger import logger

Listener = Callable[
    [events.NewMessage.Event | events.MessageDeleted.Event, list[Message]],
    Awaitable[None],
]


class TelegramMessageSourceProto(Protocol):
    @abstractmethod
    async def get_messages(self) -> list[Message]:
        pass

    @staticmethod
    def from_messages(ms: list[Message]) -> "TelegramMessageSourceProto":
        class TelegramMessageSource(TelegramMessageSourceProto):
            async def get_messages(self) -> list[Message]:
                return ms

        return TelegramMessageSource()


class TelegramMessageSource(TelegramMessageSourceProto):
    def __init__(
        self,
        client: tgclient.TgmountTelegramClient,
        chat_id: str | int,
        limit: Optional[int],
    ) -> None:
        self._client = client
        self._chat_id = chat_id
        self._limit = limit

        self._messages: Optional[list[Message]] = None

        self._client.on(events.NewMessage(chats=chat_id))(self._on_new_message)
        self._client.on(events.MessageDeleted(chats=chat_id))(self._on_delete_message)

        self._listeners = []

    def subscribe(self, listener: Listener):
        self._listeners.append(listener)

    async def _on_new_message(self, event: events.NewMessage.Event):
        if self._messages is None:
            self._messages = []

        self._messages.append(event.message)

        logger.info(f"New message: {event.message}")

        for listener in self._listeners:
            await listener(event, self._messages[:])

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

        for listener in self._listeners:
            await listener(event, self._messages[:])

    async def get_messages(self) -> list[Message]:
        if self._messages is not None:
            return self._messages[:]

        logger.info(f"Fetching {self._limit} messages from {self._chat_id}")

        self._messages = await self._client.get_messages_typed(
            self._chat_id,
            limit=self._limit,
        )

        return self._messages[:]
