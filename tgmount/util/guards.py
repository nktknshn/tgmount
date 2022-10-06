from typing import Any, TypeVar, Callable, Awaitable, TypeGuard

from telethon.tl.custom import Message

T = TypeVar("T")

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


def compose_guards(
    *gs: Callable[[Message], TypeGuard[Any]]
) -> Callable[[Message], TypeGuard[Any]]:
    return lambda m: any(map(lambda g: g(m), gs))


def compose_try_gets(*gs: Callable[[Message], T | None]) -> Callable[[Message], bool]:
    return lambda m: any(map(lambda g: g(m) is not None, gs))
