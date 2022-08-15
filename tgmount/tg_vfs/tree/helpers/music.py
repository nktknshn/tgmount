import argparse
import logging
from typing import Callable, TypedDict, TypeGuard, TypeVar, Union

from telethon.tl.custom import Message
from tgmount.tgclient.guards import *

from ..types import MessagesTreeValue, Virt

T = TypeVar("T")


def music_by_performer(
    messages: Iterable[MessageWithMusic], *, minimum=2
) -> MessagesTreeValue[MessageWithMusic]:

    perf, noperf = MessageWithMusic.group_by_performer(
        messages,
        minimum=minimum,
    )

    perf_dirs = [Virt.Dir(perf, tracks) for perf, tracks in perf.items()]

    return [
        *perf_dirs,
        *noperf,
    ]
