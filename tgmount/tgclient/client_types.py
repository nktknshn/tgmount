from abc import abstractmethod
from typing import Awaitable, Callable, Protocol

from telethon import events

from tgmount.tgclient.message_reaction_event import MessageReactionEvent
from tgmount.tgclient.message_types import MessageProto

from .types import InputDocumentFileLocation, InputPhotoFileLocation, TotalListTyped

ListenerNewMessages = Callable[[events.NewMessage.Event], Awaitable[None]]
ListenerRemovedMessages = Callable[[events.MessageDeleted.Event], Awaitable[None]]
ListenerEditedMessage = Callable[
    [events.MessageEdited.Event | MessageReactionEvent], Awaitable[None]
]


class TgmountTelegramClientEventProto(Protocol):
    @abstractmethod
    def subscribe_new_messages(self, listener: ListenerNewMessages, chats):
        pass

    @abstractmethod
    def subscribe_removed_messages(self, listener: ListenerRemovedMessages, chats):
        pass

    @abstractmethod
    def subscribe_edited_message(self, listener: ListenerEditedMessage, chats):
        pass


class TgmountTelegramClientGetMessagesProto(Protocol):
    @abstractmethod
    async def get_messages(
        self,
        *args,
        **kwargs,
    ) -> TotalListTyped[MessageProto]:
        pass


class IterDownloadProto(Protocol):
    @abstractmethod
    def __aiter__(self) -> "IterDownloadProto":
        pass

    @abstractmethod
    async def __anext__(self) -> bytes:
        pass


class TgmountTelegramClientIterDownloadProto(Protocol):
    @abstractmethod
    def iter_download(
        self,
        input_location: InputPhotoFileLocation | InputDocumentFileLocation,
        *,
        offset: int,
        request_size: int,
        limit: int,
        file_size: int,
    ) -> IterDownloadProto:
        pass


class TgmountTelegramClientDeleteMessagesProto(Protocol):
    @abstractmethod
    async def delete_messages(self, *args, **kwargs):
        pass


class TgmountTelegramClientSendMessageProto(Protocol):
    @abstractmethod
    async def send_message(self, *args, **kwargs):
        pass


class TgmountTelegramClientReaderProto(
    TgmountTelegramClientGetMessagesProto,
    TgmountTelegramClientEventProto,
    TgmountTelegramClientIterDownloadProto,
    Protocol,
):
    """Interface for client that can fetch messages and receive updates"""

    @abstractmethod
    def __init__(self, *args, **kwargs) -> None:
        pass

    @abstractmethod
    async def auth(self):
        pass


class TgmountTelegramClientWriterProto(
    TgmountTelegramClientSendMessageProto, TgmountTelegramClientDeleteMessagesProto
):
    pass
