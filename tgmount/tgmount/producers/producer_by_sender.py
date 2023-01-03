from typing import Any, Iterable, Mapping, Sequence, TypeVar

import telethon
from tgmount.tgclient.message_types import MessageProto, SenderProto
from tgmount.tgmount.error import TgmountError
from tgmount.tgmount.vfs_tree_producer_types import (
    VfsStructureConfig,
    VfsTreeProducerProto,
)
from tgmount.util import func, measure_time
from tgmount.tglog import tgmount_logger

from .grouperbase import GroupedMessages, VfsTreeProducerGrouperBase

TM = TypeVar("TM", bound=MessageProto)

Sender = Any


class MockedSender(SenderProto):
    def __init__(self, id: int, username: str) -> None:
        self.id: int = id
        self.username = username


def get_get_key(*, use_get_sender=True):
    @measure_time(logger_func=tgmount_logger.info, threshold=10)
    async def get_key(m: TM) -> str | None:

        if m.from_id is None:
            return

        if use_get_sender:
            sender = await m.get_sender()
        else:
            id = telethon.utils.get_peer_id(m.from_id)
            sender = MockedSender(id=id, username=str(id))

        key = None

        if sender is None:
            return None

        if sender.username is not None:
            key = sender.username

        if key is None:
            key = telethon.utils.get_display_name(sender)

        if key == "":
            key = None

        return key

    return get_key


async def group_by_sender(
    messages: Iterable[TM], minimum=1, use_get_sender=False
) -> tuple[Mapping[str, list[TM]], list[TM], list[TM],]:

    return await func.group_by_func_async(
        get_get_key(use_get_sender=use_get_sender),
        messages,
        minimum=minimum,
    )


class VfsTreeDirBySender(VfsTreeProducerGrouperBase, VfsTreeProducerProto):
    def __init__(
        self, tree_dir, config, resources, *, dir_structure, use_get_sender
    ) -> None:
        super().__init__(tree_dir, config, resources, dir_structure=dir_structure)
        self.use_get_sender = use_get_sender

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
            use_get_sender=arg.get("use_get_sender", False),
        )

    async def group_messages(self, messages: Iterable[MessageProto]) -> GroupedMessages:
        by_user, less, nones = await group_by_sender(
            messages, minimum=1, use_get_sender=self.use_get_sender
        )
        res = {}

        for sname, ms in by_user.items():
            sender = await ms[0].get_sender()
            if sender is None:
                continue
            _sname = f"{sender.id}_{sname}"
            res[_sname] = ms

        return res, []
