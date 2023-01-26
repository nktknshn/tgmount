from typing import (
    Callable,
    Mapping,
    Optional,
    Sequence,
    TypeVar,
    Iterator,
    overload,
)

T = TypeVar("T")


@overload
def map_keys(
    mapper: Callable[[str], str],
    d: dict[str, T],
) -> dict[str, T]:
    ...


@overload
def map_keys(
    mapper: Callable[[str], str],
    d: Mapping[str, T],
) -> Mapping[str, T]:
    ...


def map_keys(mapper, d) -> dict[str, T] | Mapping[str, T]:
    return {mapper(k): v for k, v in d.items()}


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


def dict_exclude(d: Mapping, keys: list[str]) -> dict:
    return {k: v for k, v in d.items() if not contains(k, keys)}


def get_first_key(d: Mapping, idx: int = 0) -> str | None:
    keys = list(d.keys())

    if idx > len(keys) - 1:
        return

    return keys[idx]


def get_first_pair(d: Mapping):
    return next(iter(d.items()))


Set = frozenset


def sets_difference(
    left: Set[T] | set[T], right: Set[T] | set[T]
) -> tuple[Set[T], Set[T], Set[T]]:
    unique_left = left - right
    unique_right = right - left
    common = right.intersection(left)

    return unique_left, unique_right, common


# def difference(
#     left: list[T], right: list[T], func: Callable[[T], int]
# ) -> tuple[Set[T], Set[T], Set[T]]:
#     unique_left = left - right
#     unique_right = right - left
#     common = right.intersection(left)

#     return unique_left, unique_right, common
