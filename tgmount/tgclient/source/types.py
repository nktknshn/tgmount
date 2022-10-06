from typing import Any, Awaitable, Callable, TypeVar

import telethon

T = TypeVar("T")

ReadFunctionAsync = Callable[[Any, int, int], Awaitable[bytes]]
ItemReadFactory = Callable[[T], Awaitable[ReadFunctionAsync]]

ItemReadFunctionAsync = Callable[
    [telethon.tl.custom.Message, T, int, int], Awaitable[bytes]
]

InputSourceItem = telethon.types.Photo | telethon.types.Document
