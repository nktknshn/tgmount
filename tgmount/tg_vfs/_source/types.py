from typing import Any, Awaitable, Callable, Generic, TypeVar

from tgmount import vfs
from tgmount.tgclient import Message

T = TypeVar("T")

ReadFunctionAsync = Callable[[Any, int, int], Awaitable[bytes]]
ItemReadFactory = Callable[[T], Awaitable[ReadFunctionAsync]]

ItemReadFunctionAsync = Callable[[Message, T, int, int], Awaitable[bytes]]


class TelegramFilesSourceProto(Generic[T]):
    # open
    # close
    # seek
    # tell

    async def item_read_function(
        self,
        message: Message,
        item: T,
        offset: int,
        limit: int,
    ) -> bytes:
        raise NotImplementedError()

    # async def item_to_file_content(
    #     self: "TelegramFilesSourceProto[T]",
    #     message: Message,
    #     item: T,
    # ) -> vfs.FileContent:
    #     raise NotImplementedError()
