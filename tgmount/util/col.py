from typing import Callable, Iterable, List, Optional, Sequence, TypeVar, Iterator

T = TypeVar("T")


def find(pred: Callable[[T], bool], col: Sequence[T]) -> Optional[T]:
    return next(filter(pred, col), None)


def contains(value: T, col: Sequence[T]) -> bool:
    return find(lambda a: a == value, col) is not None


def flatten(col: Iterator | list) -> list:
    res = []
    for el in col:
        if isinstance(el, (Iterator, list)):
            res.extend(flatten(el))
        else:
            res.append(el)
    return res
