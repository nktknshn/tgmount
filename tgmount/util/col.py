from typing import Callable, List, Optional, TypeVar

T = TypeVar("T")


def find(pred: Callable[[T], bool], lst: list[T]) -> Optional[T]:
    return next(filter(pred, lst), None)
