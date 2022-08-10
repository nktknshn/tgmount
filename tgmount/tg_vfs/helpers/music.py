import argparse
import logging
from typing import Callable, TypedDict, TypeGuard, TypeVar, Union

from telethon.tl.custom import Message
from tgmount.tg_vfs._tree.types import MessagesTreeValueDir, Virt
from tgmount.tgclient.search.filtering.guards import *

T = TypeVar("T")


def music_by_performer(
    messages: Iterable[MessageWithMusic], *, minimum=2
) -> MessagesTreeValueDir[MessageWithMusic]:

    perf, noperf = MessageWithMusic.group_by_performer(
        messages,
        minimum=minimum,
    )

    perf_dirs = [Virt.Dir(perf, tracks) for perf, tracks in perf.items()]

    return [
        *perf_dirs,
        *noperf,
    ]
