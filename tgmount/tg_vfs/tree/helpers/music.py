import argparse
import logging
from typing import Callable, TypedDict, TypeGuard, TypeVar, Union

from telethon.tl.custom import Message
from tgmount.tgclient.guards import *

from ..types import MessagesTreeValue, MessagesTreeValueDir, Virt

T = TypeVar("T")


def group_by_performer(
    messages: Iterable["MessageWithMusic"],
    minimum=2,
) -> tuple[dict[str, list["MessageWithMusic"]], list["MessageWithMusic"]]:

    messages = list(messages)
    no_performer = [t for t in messages if t.file.performer is None]
    with_performer = [t for t in messages if t.file.performer is not None]

    tracks = func.group_by0(lambda t: t.file.performer.lower(), with_performer)

    result = []

    for perf, tracks in tracks.items():
        if len(tracks) < minimum:
            no_performer.extend(tracks)
        else:
            result.append((perf, tracks))

    return dict(result), no_performer


def music_by_performer(
    messages: Iterable[MessageWithMusic], *, minimum=2
) -> MessagesTreeValueDir[MessageWithMusic]:

    perf, noperf = group_by_performer(
        messages,
        minimum=minimum,
    )

    perf_dirs = [Virt.Dir(perf, tracks) for perf, tracks in perf.items()]

    return [
        *perf_dirs,
        *noperf,
    ]
