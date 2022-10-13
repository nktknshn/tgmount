from abc import abstractmethod
import logging
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
from .message_source_types import (
    Arg,
    Listener,
    MessageSourceProto,
    MessageSourceSubscribableProto,
    Subscribable,
)

from .message_source_simple import MessageSourceSimple


class TelegramMessageSource(MessageSourceSimple[Message]):
    logger = tglog.getLogger("TelegramMessageSource")
    logger.setLevel(logging.ERROR)

    def __init__(
        self,
        client: TgmountTelegramClientReaderProto,
        chat_id: str | int,
        limit: Optional[int],
    ) -> None:
        self._client = client
        self._chat_id = chat_id
        self._limit = limit

        self._logger = TelegramMessageSource.logger.getChild(f"({self._chat_id})")

        super().__init__()
        self.subscribe_to_client()

    def subscribe_to_client(self):
        self._logger.info(f"Subscribing to {self._client} updates.")

        self._client.subscribe_new_messages(self._on_new_message, chats=self._chat_id)

        self._client.subscribe_removed_messages(
            self._on_delete_message, chats=self._chat_id
        )

    async def _on_new_message(self, event: events.NewMessage.Event):
        self._logger.debug(f"_on_new_message({event.message.id})")
        await self.add_messages([event.message])

    async def _on_delete_message(self, event: events.MessageDeleted.Event):
        self._logger.info(f"_on_delete_message({event.deleted_ids})")

        _msgs = []
        _removed = []

        for m in await self.get_messages():
            try:
                event.deleted_ids.index(m.id)
            except ValueError:
                _msgs.append(m)
            else:
                _removed.append(m)

        await self.set_messages(Set(_msgs))

    async def _fetch_from_client(self):
        self._logger.info(
            f"Fetching {none_fallback(self._limit, 'all')} messages from {self._chat_id}"
        )

        messages = await self._client.get_messages(self._chat_id, limit=self._limit)

        return messages

    async def get_messages(self) -> Set[Message]:
        if self._messages is None:
            messages = await self._fetch_from_client()
            await self.set_messages(Set(messages), notify=False)

        return await super().get_messages()


# class _TelegramMessageSource(MessageSourceSubscribableProto):
#     def __init__(
#         self,
#         client: TgmountTelegramClientReaderProto,
#         chat_id: str | int,
#         limit: Optional[int],
#     ) -> None:
#         self._client = client
#         self._chat_id = chat_id
#         self._limit = limit

#         self._logger = tglog.getLogger(f"TelegramMessageSource({self._chat_id})")

#         self._messages: Optional[list[Message]] = None

#         self._listeners: list[Listener] = []

#         self.event_new_messages: Subscribable = Subscribable()
#         self.event_removed_messages: Subscribable = Subscribable()

#         self._filters = []

#         self.subscribe_to_client()

#     def subscribe_to_client(self):
#         self._logger.info(f"Subscribing to {self._client} updates.")

#         # self._client.on(events.NewMessage(chats=self._chat_id))(self._on_new_message)
#         # self._client.on(events.MessageDeleted(chats=self._chat_id))(
#         #     self._on_delete_message
#         # )
#         self._client.subscribe_new_messages(self._on_new_message, chats=self._chat_id)
#         self._client.subscribe_removed_messages(
#             self._on_delete_message, chats=self._chat_id
#         )

#     @property
#     def filters(self):
#         return self._filters

#     async def _on_new_message(self, event: events.NewMessage.Event):
#         self._logger.debug(f"_on_new_message")

#         if self._messages is None:
#             self._messages = []

#         for f in self._filters:
#             if not f(event.message):
#                 self._logger.info(f"Filtered out message: {event.message}")
#                 return

#         self._messages.append(event.message)

#         self._logger.info(f"New message: {event.message}")

#         await self.event_new_messages.notify([event.message])

#         # await self.notify(self._messages[:])

#     async def _on_delete_message(self, event: events.MessageDeleted.Event):
#         self._logger.info(f"_on_delete_message({event.deleted_ids})")

#         if self._messages is None:
#             self._messages = []

#         _msgs = []
#         _removed = []

#         for m in self._messages:
#             try:
#                 event.deleted_ids.index(m.id)
#             except ValueError:
#                 _msgs.append(m)
#             else:
#                 _removed.append(m)

#         self._messages = _msgs

#         if len(_removed) > 0:
#             await self.event_removed_messages.notify(_removed)
#         else:
#             self._logger.error(f"no messages removed: {event.deleted_ids}")
#         # await self.notify(self._messages[:])

#     async def get_messages(self) -> list[Message]:
#         if self._messages is not None:
#             return self._messages[:]

#         self._logger.info(
#             f"Fetching {none_fallback(self._limit, 'all')} messages from {self._chat_id}"
#         )

#         messages = await self._client.get_messages(self._chat_id, limit=self._limit)

#         self._logger.info(f"Received {len(messages)}")

#         self._messages = []

#         for m in messages:
#             for f in self._filters:
#                 if not f(m):
#                     break
#             else:
#                 self._messages.append(m)

#         return self._messages[:]

#     def unsubscribe(self, listener: Listener[Arg]):
#         self._listeners.remove(listener)

#     @staticmethod
#     def from_messages(ms: list[Message]) -> "MessageSourceProto":
#         class TelegramMessageSource(MessageSourceProto):
#             async def get_messages(self) -> frozenset[Message]:
#                 return frozenset(ms)

#         return TelegramMessageSource()
