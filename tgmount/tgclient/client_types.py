from abc import abstractmethod
from typing import (
    Awaitable,
    Callable,
    Optional,
    Protocol,
    Sequence,
    Type,
    TypedDict,
    TypeVar,
    Union,
)

from telethon import events, hints
from tgmount.tgclient.types import TypeMessagesFilter
from .types import InputDocumentFileLocation, InputPhotoFileLocation, TotalListTyped
from telethon.tl.custom import Message

ListenerNewMessages = Callable[[events.NewMessage.Event], Awaitable[None]]
ListenerRemovedMessages = Callable[[events.MessageDeleted.Event], Awaitable[None]]


class TgmountTelegramClientEventProto(Protocol):
    @abstractmethod
    def subscribe_new_messages(self, listener: ListenerNewMessages, chats):
        pass

    @abstractmethod
    def subscribe_removed_messages(self, listener: ListenerRemovedMessages, chats):
        pass


class TgmountTelegramClientGetMessagesProto(Protocol):
    @abstractmethod
    async def get_messages(self, *args, **kwargs) -> TotalListTyped[Message]:
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
):
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


# class GetMessagesQuery(TypedDict):
#     limit: Optional[int]

#     offset_date: Optional[hints.DateLike]
#     offset_id: int
#     max_id: int
#     min_id: int
#     add_offset: int
#     search: Optional[str]
#     filter: Optional[Union[TypeMessagesFilter, Type[TypeMessagesFilter]]]
#     from_user: Optional[hints.EntityLike]
#     wait_time: Optional[float]
#     ids: Optional[Union[int, Sequence[int]]]
#     reverse: bool
#     reply_to: Optional[int]
#     scheduled: bool
