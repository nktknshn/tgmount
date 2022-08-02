import logging
from typing import (
    Awaitable,
    Callable,
    Generic,
    Optional,
    Protocol,
    Type,
    TypedDict,
    TypeGuard,
    TypeVar,
    cast,
    overload,
    Union,
    Type,
    Sequence,
)
from typing_extensions import Unpack

import telethon
from telethon import hints
from telethon import helpers
from telethon import types
from telethon.client.messages import RequestIter
from telethon.hints import EntityLike, DateLike
from telethon.client import TelegramClient
from tgmount.util import AsyncTypeGuard
from tgmount.tgclient.types import TotalListTyped

from .types import Message, Document, TypeMessagesFilter

T = TypeVar("T", contravariant=True)

logger = logging.getLogger("tgclient.search")

# helpers.TotalList
# class IterMessages(Protocol):
#     """
#     see: https://docs.telethon.dev/en/stable/modules/client.html#telethon.client.messages.MessageMethods.iter_messages
#     """

#     def iter_messages(
#         self: "TelegramClient",
#         entity: "hints.EntityLike",
#         limit: Optional[float] = None,
#         *,
#         offset_date: Optional["hints.DateLike"] = None,
#         offset_id: int = 0,
#         max_id: int = 0,
#         min_id: int = 0,
#         add_offset: int = 0,
#         search: Optional[str] = None,
#         filter: Optional[
#             "Union[types.TypeMessagesFilter, Type[types.TypeMessagesFilter]]"
#         ] = None,
#         from_user: Optional["hints.EntityLike"] = None,
#         wait_time: Optional[float] = None,
#         ids: Optional["Union[int, Sequence[int]]"] = None,
#         reverse: bool = False,
#         reply_to: Optional[int] = None,
#         scheduled: bool = False,
#     ) -> RequestIter:
#         # "Union[RequestIter, _IDsIter]":
#         pass


class GetMessagesQuery(TypedDict):
    limit: Optional[int]
    offset_id: int
    reverse: bool
    filter: Optional[Type[TypeMessagesFilter]]
    ids: Optional[list[int]]


class GetMessages(Protocol):
    async def get_messages(
        self: "GetMessages", *args, **kwargs
    ) -> TotalListTyped[Message]:
        raise NotImplementedError()


G = TypeVar("G")

MessagesFilterAsyncGuard = AsyncTypeGuard[Message, G]
MessagesFilterAsync = Callable[[Message], Awaitable[bool]]


def total_list(lst: list, total: int) -> TotalListTyped:
    res = helpers.TotalList(lst)
    res.total = total
    return cast(TotalListTyped, res)


class TelegramSearch(GetMessages):
    """
    typed methods for querying telegram
    """

    LIMIT_STEP = 100

    # XXX Type of parameter "self" must be a supertype of its class "TelegramSearch"PyrightreportGeneralTypeIssues
    # async def get_messages_typed(
    #     self: GetMessages, entity: EntityLike, **query: GetMessagesQuery  # type: ignore
    # ) -> TotalListTyped[telethon.tl.custom.Message]:
    #     return await self.get_messages(entity, **query)

    async def get_messages_typed(
        self: GetMessages,
        entity: hints.EntityLike,
        limit: Optional[int] = None,
        *,
        offset_date: Optional[hints.DateLike] = None,
        offset_id: int = 0,
        max_id: int = 0,
        min_id: int = 0,
        add_offset: int = 0,
        search: Optional[str] = None,
        filter: Optional[Union[TypeMessagesFilter, Type[TypeMessagesFilter]]] = None,
        from_user: Optional[hints.EntityLike] = None,
        wait_time: Optional[float] = None,
        ids: Optional[Union[int, Sequence[int]]] = None,
        reverse: bool = False,
        reply_to: Optional[int] = None,
        scheduled: bool = False,
    ) -> TotalListTyped[Message]:
        return await self.get_messages(
            entity,
            limit,
            offset_date=offset_date,
            offset_id=offset_id,
            max_id=max_id,
            min_id=min_id,
            add_offset=add_offset,
            search=search,
            filter=filter,
            from_user=from_user,
            wait_time=wait_time,
            ids=ids,
            reverse=reverse,
            reply_to=reply_to,
            scheduled=scheduled,
        )

    @overload
    async def get_messages_filter(
        self: GetMessages,
        entity: EntityLike,
        filter_func: MessagesFilterAsyncGuard[G],
        **query: Unpack[GetMessagesQuery],
    ) -> TotalListTyped[G]:
        ...

    @overload
    async def get_messages_filter(
        self: GetMessages,
        entity: EntityLike,
        filter_func: MessagesFilterAsync,
        **query: Unpack[GetMessagesQuery],
    ) -> TotalListTyped[Message]:
        ...

    async def get_messages_filter(
        self: GetMessages,
        entity: EntityLike,
        filter_func,
        **query: Unpack[GetMessagesQuery],
    ) -> TotalListTyped:

        """
        works as `get_messages` but tries to retrieve `limit` number of messages satisfying `filter`
        XXX fix comment
        """

        ids = query["ids"]
        limit = query["limit"]

        logger.debug(f"get_messages_filter({entity}, limit={limit}, ids={ids})")

        messages = await self.get_messages(entity, **query)
        total = messages.total
        # XXX use messages.total

        filtered_messages = [msg for msg in messages if filter_func(msg)]

        if ids is not None or limit is None:
            return total_list(filtered_messages, total)

        while limit > len(filtered_messages):
            messages = await self.get_messages(
                entity,
                **{
                    **query,
                    "limit": TelegramSearch.LIMIT_STEP,
                    "offset_id": messages[-1].id,
                },
            )

            if len(messages) == 0:
                break

            filtered_messages.extend([msg for msg in messages if filter_func(msg)])

        return total_list(filtered_messages[:limit], total)
