from typing import Iterable, Mapping

import telethon
from tgmount.tgclient.guards import MessageForwarded
from tgmount.tgmount.vfs_tree_producer_types import (
    VfsTreeProducerConfig,
    VfsTreeProducerProto,
)

from .grouperbase import GroupedMessages, VfsTreeProducerGrouperBase


async def group_by_forward(
    forwarded_messages: Iterable[MessageForwarded],
) -> Mapping[str, list[MessageForwarded]]:
    fws = {}

    for m in forwarded_messages:

        # XXX
        if m.forward is None:
            continue

        chat = await m.forward.get_chat()
        # sender = await m.forward.get_sender()
        from_name = m.forward.from_name

        dirname = (
            chat.title
            if chat is not None
            else from_name
            if from_name is not None
            else "None"
        )

        if m.forward.from_id:
            chat_type = (
                "channel"
                if m.forward.is_channel
                else "group"
                if m.forward.is_group
                else "user"
            )
            peer_id = telethon.utils.get_peer_id(m.forward.from_id)
            dirname = f"{chat_type}_{peer_id}_{dirname}"
        else:
            chat_type = "hidden"
            dirname = f"{chat_type}_{dirname}"

        if not dirname in fws:
            fws[dirname] = []

        fws[dirname].append(m)

    return fws


class VfsTreeGroupByForward(
    VfsTreeProducerGrouperBase,
    VfsTreeProducerProto,
):
    @classmethod
    async def from_config(
        cls, resources, config: VfsTreeProducerConfig, arg: Mapping, sub_dir
    ):

        return VfsTreeGroupByForward(
            config=config,
            dir_structure=arg.get(
                "dir_structure",
                VfsTreeGroupByForward.DEFAULT_ROOT_CONFIG,
            ),
            resources=resources,
            tree_dir=sub_dir,
        )

    async def group_messages(
        self, messages: Iterable[MessageForwarded]
    ) -> GroupedMessages[MessageForwarded]:
        return await group_by_forward(messages), []
