from typing import TypeVar
from tgmount.tgclient.message_source import Set

T = TypeVar("T")


def to_list_of_single_key_dicts(
    items: list[str | dict[str, dict]]
) -> list[str | dict[str, dict]]:
    res = []

    for item in items:
        if isinstance(item, str):
            res.append(item)
        else:
            res.extend(dict([t]) for t in item.items())

    return res


# def sets_difference(left: Set[T], right: Set[T]) -> tuple[Set[T], Set[T], Set[T]]:
#     unique_left = left - right
#     unique_right = right - left
#     common = right.intersection(left)
#
#     return unique_left, unique_right, common
