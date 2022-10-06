from typing import Optional, TypeGuard, TypeVar

from .col import find, sets_difference
from .guards import compose_guards

T = TypeVar("T")


def none_fallback(value: Optional[T], default: T) -> T:
    return value if value is not None else default


def is_not_none(value: Optional[T]) -> TypeGuard[T]:
    return value is not None


def int_or_string(value: int | str):
    try:
        return int(value)
    except ValueError:
        return str(value)
