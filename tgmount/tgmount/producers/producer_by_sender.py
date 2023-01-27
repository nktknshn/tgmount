from typing import Iterable, Mapping

import telethon

from tgmount.tgclient.message_types import MessageProto
from tgmount.tgmount.vfs_tree_producer_types import (
    VfsTreeProducerConfig,
    VfsTreeProducerProto,
)
from tgmount.util import func, measure_time

from .grouperbase import GroupedMessages, VfsTreeProducerGrouperBase


from .logger import module_logger as _logger


def get_get_key(*, use_get_sender=True):
    """Retuns a async function that gets from a message a key for grouping"""

    @measure_time(logger_func=_logger.getChild("VfsTreeDirBySender").info, threshold=3)
    async def get_key(m: MessageProto) -> str | None:

        if m.from_id is None:
            return

        sender_id = telethon.utils.get_peer_id(m.from_id)

        if use_get_sender:
            sender = await m.get_sender()
            key = None

            if sender is None:
                return None

            if sender.username is not None:
                key = sender.username

            if key is None:
                key = telethon.utils.get_display_name(sender)

            if key == "":
                key = None

            return f"{sender_id}_{key}"
        else:
            # sender = MockedSender(id=id, username=str(id))
            return str(sender_id)

    return get_key


async def group_by_sender(
    messages: Iterable[MessageProto], minimum=1, use_get_sender=False
) -> tuple[Mapping[str, list[MessageProto]], list[MessageProto], list[MessageProto],]:

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
        cls, resources, config: VfsTreeProducerConfig, arg: Mapping, sub_dir
    ):

        return VfsTreeDirBySender(
            resources=resources,
            tree_dir=sub_dir,
            config=config,
            dir_structure=arg.get(
                "dir_structure",
                VfsTreeDirBySender.DEFAULT_ROOT_CONFIG,
            ),
            use_get_sender=arg.get("use_get_sender", True),
        )

    async def group_messages(self, messages: Iterable[MessageProto]) -> GroupedMessages:

        by_user, less, nones = await group_by_sender(
            messages, minimum=1, use_get_sender=self.use_get_sender
        )

        res = {}

        for sname, sender_messages in by_user.items():
            res[sname] = sender_messages

        return res, []
