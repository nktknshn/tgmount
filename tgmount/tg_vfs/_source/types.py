from typing import Any, Awaitable, Callable, Generic, Protocol, TypeVar

from tgmount import vfs
from tgmount.tgclient import Message

T = TypeVar("T")

ReadFunctionAsync = Callable[[Any, int, int], Awaitable[bytes]]
ItemReadFactory = Callable[[T], Awaitable[ReadFunctionAsync]]

ItemReadFunctionAsync = Callable[[Message, T, int, int], Awaitable[bytes]]


class TelegramFilesSourceProto(Protocol[T]):
    async def item_read_function(
        self,
        message: Message,
        item: T,
        offset: int,
        limit: int,
    ) -> bytes:
        raise NotImplementedError()
