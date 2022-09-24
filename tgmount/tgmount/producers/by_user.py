from typing import Awaitable, Callable, Iterable, Mapping, TypedDict, TypeVar

import telethon
from telethon.tl.custom import Message
from tgmount.util import col


_MT1 = TypeVar("_MT1", bound=Message)


async def group_by_sender(
    messages: Iterable[_MT1], minimum=1
) -> tuple[Mapping[str, list[_MT1]], list[_MT1], list[_MT1],]:
    async def get_key(m: _MT1) -> str | None:
        sender = await m.get_sender()

        key = None

        if sender is None:
            return None

        if sender.username:
            key = sender.username

        if key is None:
            key = telethon.utils.get_display_name(sender)

        if key == "":
            key = None

        return key

    return await col.group_by_func_async(
        get_key,
        messages,
        minimum=minimum,
    )
