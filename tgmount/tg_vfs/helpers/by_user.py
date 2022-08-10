import telethon
from typing import Callable, Iterable, Mapping, TypeVar, TypedDict

# from tgmount.tgclient.types import Message
from tgmount.tg_vfs._tree.types import MessagesTree, MessagesTreeValue
from tgmount.util import func

from telethon.tl.custom import Message

_M = TypeVar("_M", bound=Message)

_T1 = TypeVar("_T1")
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

    return await func.group_by_func_async(
        get_key,
        messages,
        minimum=minimum,
    )


async def messages_by_user(messages: Iterable[_M], *, minimum=1) -> MessagesTree[_M]:
    by_user, less, nones = await group_by_sender(
        messages,
        minimum=minimum,
    )

    return {
        **by_user,
        "None": nones,
        "Other": less,
    }


def messages_by_user_func(
    func: Callable[
        [Mapping[str, list[_M]], list[_M], list[_M]],
        MessagesTree | MessagesTreeValue,
    ]
):
    async def _inner(messages: Iterable[_M], *, minimum=1):

        by_user, less, nones = await group_by_sender(
            messages,
            minimum=minimum,
        )

        return func(by_user, less, nones)

    return _inner


def messages_by_user_simple(
    func: Callable[
        [Mapping[str, list[Message]], list[Message], list[Message]],
        MessagesTree[Message],
    ]
):
    async def _inner(messages: Iterable[Message], *, minimum=1):

        by_user, less, nones = await group_by_sender(
            messages,
            minimum=minimum,
        )

        return func(by_user, less, nones)

    return _inner
