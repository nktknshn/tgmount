import copy

from telethon import events

from tgmount import config
from tgmount.tgclient.client_types import TgmountTelegramClientGetMessagesProto
from tgmount.tgclient.message_reaction_event import MessageReactionEvent
from tgmount.tgclient.message_source_types import MessageSourceProto
from tgmount.tgclient.message_types import MessageProto

from .logger import logger as _logger
from .message_source import MessageSource

EntityId = str | int
EventType = (
    events.NewMessage.Event
    | events.MessageDeleted.Event
    | events.MessageEdited.Event
    | MessageReactionEvent.Event
)


class TelegramEventsDispatcher:
    """
    Connects TelegramClient to MessageSources. Receives telethon.events and passes them to the corresponding messages sources.

    Puts events in a queue when paused

    Use `resume` method to pass the enqueued events to message sources
    """

    logger = _logger.getChild("TelegramEventsDispatcher")

    def __init__(self) -> None:
        # self._client = client
        self._sources: dict[EntityId, MessageSourceProto[MessageProto]] = {}

        self._sources_events_queue: dict[EntityId, list[EventType]] = {}

        self._is_paused = True

    @property
    def is_paused(self):
        return self._is_paused

    def connect(
        self,
        entity_id: EntityId,
        source: MessageSourceProto[MessageProto],
    ):
        """events from `entity_id` will be turned into `MessageSource` methods calls"""

        self.logger.trace(f"connect({entity_id})")
        self._sources[entity_id] = source

    async def process_new_message_event(self, chat_id, ev):
        await self._on_new_message(chat_id, ev)

    async def process_delete_message_event(self, chat_id, ev):
        await self._on_delete_message(chat_id, ev)

    async def process_edited_message_event(self, chat_id, ev):
        await self._on_edited_message(chat_id, ev)

    def _get_total(self):
        total = {}
        for k, v in self._sources_events_queue.items():
            total[k] = len(v)
        return total

    async def _enqueue_event(
        self,
        chat_id: EntityId,
        event: EventType,
    ):
        self.logger.debug(
            f"_enqueue_event: {event.__class__}. Total events enqued: {self._get_total()}"
        )

        q = self._sources_events_queue.get(chat_id, [])
        q.append(event)
        self._sources_events_queue[chat_id] = q

    async def _on_edited_message(
        self,
        chat_id: EntityId,
        event: events.MessageEdited.Event | MessageReactionEvent.Event,
    ):
        if self.is_paused:
            await self._enqueue_event(chat_id, event)
            return

        if isinstance(event, events.MessageEdited.Event):
            self.logger.debug(f"_on_edited_message: {event.id}")
        else:
            self.logger.debug(
                f"_on_edited_message: message {event.msg_id} reactions update {event.reactions}"
            )

        source = self._sources.get(chat_id)

        if source is None:
            self.logger.error(f"_on_edited_message: Missing {chat_id}")
            return

        if isinstance(event, MessageReactionEvent.Event):
            messages = await source.get_by_ids([event.msg_id])

            if messages is None or len(messages) == 0:
                self.logger.error(
                    f"_on_edited_message: Missing message with id {event.msg_id}"
                )
                return

            message = copy.copy(messages[0])
            message.reactions = event.reactions

            await source.edit_messages([message])
        else:
            self.logger.debug(
                f"Edited message: {MessageProto.repr_short(event.message)}"
            )
            await source.edit_messages([event.message])

    async def _on_new_message(self, chat_id: EntityId, event: events.NewMessage.Event):
        self.logger.debug(f"New message: {MessageProto.repr_short(event.message)}")

        self.logger.trace(event.message)

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
        self.logger.debug(f"Removed messages: {event.deleted_ids} from {chat_id}")

        if self.is_paused:
            await self._enqueue_event(chat_id, event)
            return

        source = self._sources.get(chat_id)

        if source is None:
            self.logger.error(f"_on_delete_message: Missing {chat_id}")
            return

        await source.remove_messages_ids(event.deleted_ids)

    async def pause(self):
        """Stops dispatching events"""
        self._is_paused = True

    async def resume(self):
        """Dispatches the accumulated events to sources"""
        self._is_paused = False
        self.logger.debug(f"resume(). Total events enqued: {self._get_total()}")

        for chat_id, q in self._sources_events_queue.items():
            self.logger.debug(f"Resume {chat_id}, {len(q)} events")

            for ev in q:
                if isinstance(ev, events.NewMessage.Event):
                    await self._on_new_message(chat_id, ev)
                elif isinstance(
                    ev, (events.MessageEdited.Event, MessageReactionEvent.Event)
                ):
                    await self._on_edited_message(chat_id, ev)
                elif isinstance(ev, events.MessageDeleted().Event):
                    await self._on_delete_message(chat_id, ev)
                else:
                    self.logger.error(f"Invalid event type: {ev}")
