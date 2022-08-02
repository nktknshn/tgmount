from typing import Any, Awaitable, Callable, Optional, Protocol, Generic, TypeVar

import telethon
from tgmount import vfs
from tgmount.tgclient import Message

from .types import TelegramFilesSourceProto

T = TypeVar("T")


class TelegramFilesSourceBase(TelegramFilesSourceProto[T]):
    pass
    # open
    # close
    # seek
    # tell

    # def get_read_function(
    #     self,
    #     message: Message,
    #     document: T,
    # ) -> Callable[[int, int], Awaitable[bytes]]:
    #     async def _inn(offset: int, limit: int) -> bytes:
    #         return await self.item_read_function(message, document, offset, limit)

    #     return _inn
