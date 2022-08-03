import logging
from typing import (
    Type,
)


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
