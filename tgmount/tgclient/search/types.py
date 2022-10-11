from typing import (
    Awaitable,
    Callable,
    Optional,
    Protocol,
    Sequence,
    Type,
    TypeVar,
    TypedDict,
    Union,
)


TT = TypeVar("TT")


class TotalListTyped(list[TT]):
    total: int
