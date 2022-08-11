from typing import (
    Awaitable,
    Callable,
    Optional,
    Protocol,
    Sequence,
    Type,
    TypeVar,
    TypedDict,
    Union,
)
import telethon
from telethon import hints
from telethon import helpers
from telethon import types
from telethon.client.messages import RequestIter
from telethon.hints import EntityLike, DateLike
from telethon.client import TelegramClient

# from tgmount.util import AsyncTypeGuard
from tgmount.tgclient.types import Message, TypeMessagesFilter
from tgmount.util.guards import SyncTypeGuard

T = TypeVar("T", contravariant=True)

TT = TypeVar("TT")


class TotalListTyped(list[TT]):
    total: int


class GetMessagesQuery(TypedDict):
    limit: Optional[int]

    offset_date: Optional[hints.DateLike]
    offset_id: int
    max_id: int
    min_id: int
    add_offset: int
    search: Optional[str]
    filter: Optional[Union[TypeMessagesFilter, Type[TypeMessagesFilter]]]
    from_user: Optional[hints.EntityLike]
    wait_time: Optional[float]
    ids: Optional[Union[int, Sequence[int]]]
    reverse: bool
    reply_to: Optional[int]
    scheduled: bool


class GetMessages(Protocol):
    async def get_messages(
        self: "GetMessages", *args, **kwargs
    ) -> TotalListTyped[Message]:
        raise NotImplementedError()


G = TypeVar("G")

# MessagesFilterAsyncGuard = AsyncTypeGuard[Message, G]
MessagesFilterAsync = Callable[[Message], Awaitable[bool]]

# MessagesFilterGuard = SyncTypeGuard[Message, G]
MessagesFilter = Callable[[Message], bool]
