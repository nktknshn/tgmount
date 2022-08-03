import logging
from typing import TypeVar, overload

from telethon import hints
from tgmount.tgclient.types import Message
from typing_extensions import Unpack

from .types import (
    GetMessages,
    GetMessagesQuery,
    MessagesFilterAsync,
    MessagesFilterAsyncGuard,
    TotalListTyped,
)
from .util import total_list
from .mixins import TelegramSearch

G = TypeVar("G")

logger = logging.getLogger("tgmount-tgclient")


# class SearchFiltering:
#     @overload
#     async def get_messages_filter(
#         self: GetMessages,
#         entity: hints.EntityLike,
#         filter_func: MessagesFilterAsyncGuard[G],
#         **query: Unpack[GetMessagesQuery],
#     ) -> TotalListTyped[G]:
#         ...

#     @overload
#     async def get_messages_filter(
#         self: GetMessages,
#         entity: hints.EntityLike,
#         filter_func: MessagesFilterAsync,
#         **query: Unpack[GetMessagesQuery],
#     ) -> TotalListTyped[Message]:
#         ...

#     async def get_messages_filter(
#         self: GetMessages,
#         entity: hints.EntityLike,
#         filter_func,
#         **query: Unpack[GetMessagesQuery],
#     ) -> TotalListTyped:

#         """
#         works as `get_messages` but tries to retrieve `limit` number of messages satisfying `filter`
#         XXX fix comment
#         """

#         ids = query["ids"]
#         limit = query["limit"]

#         logger.debug(f"get_messages_filter({entity}, limit={limit}, ids={ids})")

#         messages = await self.get_messages(entity, **query)
#         total = messages.total
#         # XXX use messages.total

#         filtered_messages = [msg for msg in messages if filter_func(msg)]

#         if ids is not None or limit is None:
#             return total_list(filtered_messages, total)

#         while limit > len(filtered_messages):
#             messages = await self.get_messages(
#                 entity,
#                 **{
#                     **query,
#                     "limit": TelegramSearch.LIMIT_STEP,
#                     "offset_id": messages[-1].id,
#                 },
#             )

#             if len(messages) == 0:
#                 break

#             filtered_messages.extend([msg for msg in messages if filter_func(msg)])

#         return total_list(filtered_messages[:limit], total)
