from typing import (
    Awaitable,
    Callable,
    Generic,
    Optional,
    Protocol,
    Sequence,
    Type,
    TypedDict,
    TypeGuard,
    TypeVar,
    Union,
    cast,
    overload,
)

from telethon import hints
import telethon

from tgmount.tgclient.types import TypeMessagesFilter

Message = telethon.tl.custom.Message

from .types import GetMessages, TotalListTyped


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
