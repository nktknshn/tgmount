from typing import (
    Optional,
    Sequence,
    Type,
    Union,
)

import telethon
from telethon import hints

from tgmount.tgclient.types import TypeMessagesFilter

Message = telethon.tl.custom.Message

from ..types import TotalListTyped
from ..client_types import TgmountTelegramClientGetMessagesProto


class TelegramSearch(TgmountTelegramClientGetMessagesProto):
    """
    typed methods for querying telegram
    """

    LIMIT_STEP = 100

    # XXX Type of parameter "self" must be a supertype of its class "TelegramSearch"PyrightreportGeneralTypeIssues
    # async def get_messages_typed(
    #     self: GetMessages, entity: EntityLike, **query: GetMessagesQuery  # type: ignore
    # ) -> TotalListTyped[telethon.tl.custom.Message]:
    #     return await self.get_messages(entity, **query)

    async def get_messages(
        self,
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
        ...
