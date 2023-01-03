from typing import Mapping, Optional

from telethon import events
from telethon.tl.custom import Message

from tgmount import tglog, config
from tgmount.tgclient.client_types import (
    TgmountTelegramClientEventProto,
    TgmountTelegramClientReaderProto,
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


# class TelegramMessageSource(MessageSourceSubscribableProto):
#     logger = tglog.getLogger("TelegramMessageSource")

#     def __init__(self) -> None:
#         self.event_new_messages: SubscribableProto[Set[Message]] = Subscribable()
#         self.event_removed_messages: SubscribableProto[Set[Message]] = Subscribable()
#         self.source = MessageSourceSimple()

#     async def get_messages(self) -> Set[Message]:
#         pass


ChatId = str | int


class TelegramEventsDispatcher:
    """
    Receives telethon.events and passes them to corresponding messages sources.

    Accumulates events if paused

    Use `resume` method to pass the accumulated events to message sources
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

    def register_source(
        self,
        chat_id: ChatId,
        source: MessageSourceSimple,
    ):
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

    # def subscribe_to_client(self):
    #     self.logger.info(f"Subscribing to {self._client} updates.")

    # self._client.subscribe_new_messages(self._on_new_message, chats=self._chat_id)
    # self._client.subscribe_removed_messages(
    #     self._on_delete_message, chats=self._chat_id
    # )

    # def add_client(self, )


class TelegramMessagesFetcher:
    """Fetches messages"""

    def __init__(
        self,
        client: TgmountTelegramClientReaderProto,
        cfg: config.MessageSource,
    ) -> None:
        self.client = client
        self.cfg = cfg

    async def fetch(
        self,
    ):
        return await self.client.get_messages(
            self.cfg.entity,
            limit=self.cfg.limit,
        )


class TelegramMessageSource:
    """ """

    logger = tglog.getLogger("TelegramMessageSource")
    # logger.setLevel(logging.ERROR)

    def __init__(
        self,
        client: TgmountTelegramClientReaderProto,
        chat_id: str | int,
        limit: Optional[int],
        receive_updates=True,
    ) -> None:
        self._client = client
        self._chat_id = chat_id
        self._limit = limit

        self.receive_updates = receive_updates

        super().__init__()

        self._logger = self.logger.getChild(f"{self._chat_id}")

        # if self._receive_updates:
        #     self.subscribe_to_client()

    # def subscribe_to_client(self):
    #     self._logger.info(f"Subscribing to {self._client} updates.")

    #     self._client.subscribe_new_messages(self._on_new_message, chats=self._chat_id)

    #     self._client.subscribe_removed_messages(
    #         self._on_delete_message, chats=self._chat_id
    #     )

    # async def _on_new_message(self, event: events.NewMessage.Event):
    #     self._logger.info(f"New message: {event.message}")

    #     await self.add_messages([event.message])

    # async def _on_delete_message(self, event: events.MessageDeleted.Event):
    #     self._logger.info(f"Removed messages:{event.deleted_ids}")

    #     _msgs = []
    #     _removed = []

    #     for m in await self.get_messages():
    #         try:
    #             event.deleted_ids.index(m.id)
    #         except ValueError:
    #             _msgs.append(m)
    #         else:
    #             self._logger.info(f"Removed message:{m}")
    #             _removed.append(m)

    #     await self.remove_messages(Set(_removed))

    async def fetch_from_client(self):
        self._logger.info(
            f"Fetching {none_fallback(self._limit, 'all')} messages from {self._chat_id}"
        )

        messages = await self._client.get_messages(self._chat_id, limit=self._limit)

        return messages

    # async def get_messages(self) -> Set[Message]:
    #     if self._messages is None:
    #         messages = await self._fetch_from_client()
    #         await self.set_messages(Set(messages), notify=False)

    #     return await super().get_messages()
