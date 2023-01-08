from typing import Mapping, Optional

from telethon import events
from telethon.tl.custom import Message

from tgmount import tglog, config
from tgmount.tgclient.client_types import (
    TgmountTelegramClientEventProto,
    TgmountTelegramClientReaderProto,
    TgmountTelegramClientGetMessagesProto,
)
from tgmount.tgclient.message_source_types import (
    MessageSourceSubscribableProto,
    Subscribable,
    SubscribableProto,
)
from tgmount.util import none_fallback
from tgmount.tgmount.types import Set

from .message_source_simple import MessageSourceSimple
from tgmount.vfs.util import MyLock


class MessagesDisptacher:
    async def add_message_source(
        self, name: str, source: MessageSourceSubscribableProto
    ):
        pass

    async def _on_new_message(self, source, message):
        pass

    async def _on_removed_messages(self, source, messages):
        pass


ChatId = str | int


class TelegramEventsDispatcher:
    """
    Connects TelegramClient to MessageSources. Receives telethon.events and passes them to corresponding messages sources.

    Enques events when paused

    Use `resume` method to pass the enqued events to message sources
    """

    logger = tglog.getLogger("TelegramEventsDispatcher")

    def __init__(self, client: TgmountTelegramClientEventProto) -> None:
        self._client = client
        self._sources: dict[ChatId, MessageSourceSimple] = {}

        self._sources_events_queue: dict[
            ChatId, list[events.NewMessage.Event | events.MessageDeleted.Event]
        ] = {}

        self._paused = True

    @property
    def is_paused(self):
        return self._paused

    def connect(
        self,
        chat_id: ChatId,
        source: MessageSourceSimple,
    ):
        """events from `chat_id` will be turned into `MessageSourceSimple` methods calls"""
        self._sources[chat_id] = source

        self._client.subscribe_new_messages(
            lambda ev: self._on_new_message(chat_id, ev), chats=chat_id
        )

        self._client.subscribe_removed_messages(
            lambda ev: self._on_delete_message(chat_id, ev), chats=chat_id
        )

    async def _enqueue_event(
        self,
        chat_id: ChatId,
        event: events.NewMessage.Event | events.MessageDeleted.Event,
    ):
        q = self._sources_events_queue.get(chat_id, [])
        q.append(event)
        self._sources_events_queue[chat_id] = q

    async def _on_new_message(self, chat_id: ChatId, event: events.NewMessage.Event):
        self.logger.info(f"New message: {event.message}")

        if self.is_paused:
            await self._enqueue_event(chat_id, event)
            return

        source = self._sources.get(chat_id)

        if source is None:
            self.logger.error(f"_on_new_message: Missing {chat_id}")
            return

        await source.add_messages([event.message])

    async def _on_delete_message(
        self, chat_id: ChatId, event: events.MessageDeleted.Event
    ):
        self.logger.info(f"Removed messages:{event.deleted_ids}")

        if self.is_paused:
            await self._enqueue_event(chat_id, event)
            return

        source = self._sources.get(chat_id)

        if source is None:
            self.logger.error(f"_on_new_message: Missing {chat_id}")
            return

        _msgs = []
        _removed = []

        for m in await source.get_messages():
            try:
                event.deleted_ids.index(m.id)
            except ValueError:
                _msgs.append(m)
            else:
                self.logger.info(f"Removed message:{m}")
                _removed.append(m)

        await source.remove_messages(Set(_removed))

    async def pause(self):
        """Stops dispatching events"""
        self._paused = True

    async def resume(self):
        """Dispatches the accumulated events to sources"""
        self._paused = False
        self.logger.info(f"resume")
        for chat_id, q in self._sources_events_queue.items():
            self.logger.info(f"resume {chat_id}, {len(q)} events")
            for ev in q:
                if isinstance(ev, events.NewMessage.Event):
                    await self._on_new_message(chat_id, ev)
                else:
                    await self._on_delete_message(chat_id, ev)


class TelegramMessagesFetcher:
    """Fetches messages for building initial vfs tree"""

    def __init__(
        self, client: TgmountTelegramClientGetMessagesProto, cfg: config.MessageSource
    ) -> None:
        self.client = client
        self.cfg = cfg

    async def fetch(self):
        return await self.client.get_messages(
            self.cfg.entity,
            limit=self.cfg.limit,
        )


# class TelegramMessageSource:
#     """ """

#     logger = tglog.getLogger("TelegramMessageSource")
#     # logger.setLevel(logging.ERROR)

#     def __init__(
#         self,
#         client: TgmountTelegramClientReaderProto,
#         chat_id: str | int,
#         limit: Optional[int],
#         receive_updates=True,
#     ) -> None:
#         self._client = client
#         self._chat_id = chat_id
#         self._limit = limit

#         self.receive_updates = receive_updates

#         super().__init__()

#         self._logger = self.logger.getChild(f"{self._chat_id}")

#     async def fetch_from_client(self):
#         self._logger.info(
#             f"Fetching {none_fallback(self._limit, 'all')} messages from {self._chat_id}"
#         )

#         messages = await self._client.get_messages(self._chat_id, limit=self._limit)

#         return messages
