from typing import Callable, List, Optional, Sequence, TypeVar

T = TypeVar("T")


def find(pred: Callable[[T], bool], col: Sequence[T]) -> Optional[T]:
    return next(filter(pred, col), None)


def contains(value: T, col: Sequence[T]) -> bool:
    return find(lambda a: a == value, col) is not None
