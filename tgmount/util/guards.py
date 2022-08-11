from typing import Any, TypeVar, Callable, Awaitable, TypeGuard, overload

from telethon.tl.custom import Message

_I = TypeVar("_I")
_O = TypeVar("_O")
_O2 = TypeVar("_O2")

AsyncTypeGuard = Callable[[_I], Awaitable[TypeGuard[_O]]]
SyncTypeGuard = Callable[[_I], TypeGuard[_O]]


def compose_async_guards(
    g1: AsyncTypeGuard[_I, _O],
    g2: AsyncTypeGuard[_I, _O2],
) -> AsyncTypeGuard[_I, _O | _O2]:
    async def _inner(inp: _I) -> TypeGuard[_O | _O2]:
        return await g1(inp) or await g2(inp)

    return _inner


def compose_guards_or(
    g1: Callable[[_I], TypeGuard[_O]],
    g2: Callable[[_I], TypeGuard[_O2]],
) -> Callable[[_I], TypeGuard[_O | _O2]]:
    def _inner(inp: _I) -> TypeGuard[_O | _O2]:
        return g1(inp) or g2(inp)

    return _inner


# @overload
# def guards(
#     g: Callable[[Message], TypeGuard[Any]],
# ) -> Callable[[Message], bool]:
#     ...


def guards(
    *gs: Callable[[Message], TypeGuard[Any]]
) -> Callable[[Message], TypeGuard[Message]]:
    return lambda m: any(map(lambda g: g(m), gs))
