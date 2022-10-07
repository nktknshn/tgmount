from typing import Any, Iterable, Mapping, Sequence, TypeVar

import telethon
from telethon.tl.custom import Message
from tgmount.tgmount.error import TgmountError
from tgmount.tgmount.vfs_tree_producer_types import (
    VfsStructureConfig,
    VfsTreeProducerProto,
)
from tgmount.util import func

from .grouperbase import GroupedMessages, VfsTreeProducerGrouperBase

TM = TypeVar("TM", bound=Message)

Sender = Any


async def get_key(m: TM) -> str | None:
    sender = await m.get_sender()

    key = None

    if sender is None:
        return None

    if sender.username:
        key = sender.username

    if key is None:
        key = telethon.utils.get_display_name(sender)

    if key == "":
        key = None

    return key


async def group_by_sender(
    messages: Iterable[TM], minimum=1
) -> tuple[Mapping[str, list[TM]], list[TM], list[TM],]:

    return await func.group_by_func_async(
        get_key,
        messages,
        minimum=minimum,
    )


class VfsTreeDirBySender(VfsTreeProducerGrouperBase, VfsTreeProducerProto):
    @classmethod
    async def from_config(
        cls, resources, config: VfsStructureConfig, arg: Mapping, sub_dir
    ):

        if config.producer_config is None:
            raise TgmountError(f"Missing producer config at: {sub_dir.path}")

        return VfsTreeDirBySender(
            resources=resources,
            tree_dir=sub_dir,
            config=config.producer_config,
            dir_structure=arg.get(
                "dir_structure",
                VfsTreeDirBySender.DEFAULT_ROOT_CONFIG,
            ),
        )

    async def group_messages(self, messages: Iterable[Message]) -> GroupedMessages:
        by_user, less, nones = await group_by_sender(messages, minimum=1)
        res = {}

        for sname, ms in by_user.items():
            sender = await ms[0].get_sender()
            if sender is None:
                continue
            _sname = f"{sender.id}_{sname}"
            res[_sname] = ms

        return res, []
