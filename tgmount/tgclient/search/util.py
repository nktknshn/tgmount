from typing import cast
from telethon import hints
from telethon import helpers
from .types import TotalListTyped


def total_list(lst: list, total: int) -> TotalListTyped:
    res = helpers.TotalList(lst)
    res.total = total
    return cast(TotalListTyped, res)
