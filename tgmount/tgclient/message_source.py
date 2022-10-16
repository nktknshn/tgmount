from typing import Optional

from telethon import events
from telethon.tl.custom import Message

from tgmount import tglog
from tgmount.tgclient.client_types import TgmountTelegramClientReaderProto
from tgmount.util import none_fallback
from tgmount.tgmount.types import Set

from .message_source_simple import MessageSourceSimple
from tgmount.vfs.util import MyLock


class TelegramMessageSource(MessageSourceSimple[Message]):
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

        self._receive_updates = receive_updates

        super().__init__()

        self._logger = TelegramMessageSource.logger.getChild(f"{self._chat_id}")

        if self._receive_updates:
            self.subscribe_to_client()

    def subscribe_to_client(self):
        self._logger.info(f"Subscribing to {self._client} updates.")

        self._client.subscribe_new_messages(self._on_new_message, chats=self._chat_id)

        self._client.subscribe_removed_messages(
            self._on_delete_message, chats=self._chat_id
        )

    async def _on_new_message(self, event: events.NewMessage.Event):
        self._logger.info(f"New message: {event.message}")

        await self.add_messages([event.message])

    async def _on_delete_message(self, event: events.MessageDeleted.Event):
        self._logger.info(f"Removed messages:{event.deleted_ids}")

        _msgs = []
        _removed = []

        for m in await self.get_messages():
            try:
                event.deleted_ids.index(m.id)
            except ValueError:
                _msgs.append(m)
            else:
                self._logger.info(f"Removed message:{m}")
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
