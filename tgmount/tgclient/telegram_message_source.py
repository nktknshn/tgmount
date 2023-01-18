from telethon import events

from tgmount import config, tglog
from tgmount.tgclient.client_types import TgmountTelegramClientGetMessagesProto
from tgmount.tgclient.message_source_types import MessageSourceSubscribableProto
from tgmount.tgmount.types import Set

from .message_source import MessageSource

from .logger import logger as _logger


class MessagesDisptacher:
    async def add_message_source(
        self, name: str, source: MessageSourceSubscribableProto
    ):
        pass

    async def _on_new_message(self, source, message):
        pass

    async def _on_removed_messages(self, source, messages):
        pass


EntityId = str | int


class TelegramEventsDispatcher:
    """
    Connects TelegramClient to MessageSources. Receives telethon.events and passes them to corresponding messages sources.

    Enques events when paused

    Use `resume` method to pass the enqued events to message sources
    """

    logger = _logger.getChild("TelegramEventsDispatcher")

    def __init__(self) -> None:
        # self._client = client
        self._sources: dict[EntityId, MessageSource] = {}

        self._sources_events_queue: dict[
            EntityId, list[events.NewMessage.Event | events.MessageDeleted.Event]
        ] = {}

        self._paused = True

    @property
    def is_paused(self):
        return self._paused

    def connect(
        self,
        entity_id: EntityId,
        source: MessageSource,
    ):
        """events from `entity_id` will be turned into `MessageSourceSimple` methods calls"""

        self.logger.debug(f"connect({entity_id})")
        self._sources[entity_id] = source

    async def process_new_message_event(self, chat_id, ev):
        await self._on_new_message(chat_id, ev)

    async def process_delete_message_event(self, chat_id, ev):
        await self._on_delete_message(chat_id, ev)

    def _get_total(self):
        total = {}
        for k, v in self._sources_events_queue.items():
            total[k] = len(v)
        return total

    async def _enqueue_event(
        self,
        chat_id: EntityId,
        event: events.NewMessage.Event | events.MessageDeleted.Event,
    ):
        self.logger.info(f"_enqueue_event: {event}. Total events: {self._get_total()}")

        q = self._sources_events_queue.get(chat_id, [])
        q.append(event)
        self._sources_events_queue[chat_id] = q

    async def _on_new_message(self, chat_id: EntityId, event: events.NewMessage.Event):
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
        self, chat_id: EntityId, event: events.MessageDeleted.Event
    ):
        self.logger.info(f"Removed messages: {event.deleted_ids} from {chat_id}")

        if self.is_paused:
            await self._enqueue_event(chat_id, event)
            return

        source = self._sources.get(chat_id)

        if source is None:
            self.logger.error(f"_on_delete_message: Missing {chat_id}")
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
        self.logger.info(f"resume(). Total enqued: {self._get_total()}")

        for chat_id, q in self._sources_events_queue.items():
            self.logger.debug(f"Resume {chat_id}, {len(q)} events")

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
