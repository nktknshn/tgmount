from typing import Iterable, Mapping, TypeVar
from tgmount.tgclient.guards import MessageWithMusic
from tgmount.tgmount.producers.grouperbase import (
    GroupedMessages,
    VfsTreeProducerGrouperBase,
)
from tgmount.tgmount.vfs_tree import VfsTreeDir
from tgmount.tgmount.vfs_tree_producer_types import (
    VfsDirConfig,
    VfsTreeProducerConfig,
    VfsTreeProducerProto,
)
from tgmount.tgmount.error import TgmountError
from tgmount.util import func, none_fallback

T = TypeVar("T")


def group_by_performer(
    messages: Iterable[MessageWithMusic],
    minimum=1,
) -> tuple[dict[str, list[MessageWithMusic]], list[MessageWithMusic]]:

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


class VfsTreeGroupByPerformer(VfsTreeProducerGrouperBase, VfsTreeProducerProto):
    @classmethod
    async def from_config(
        cls, resources, config: VfsTreeProducerConfig, arg: Mapping, sub_dir: VfsTreeDir
    ):

        # if config.vfs_producer_config is None:
        #     raise TgmountError(f"Missing producer config at: {sub_dir.path}")

        # vfs_producer_arg = none_fallback(config.vfs_producer_arg, {})

        return VfsTreeGroupByPerformer(
            config=config,
            dir_structure=arg.get(
                "dir_structure",
                VfsTreeGroupByPerformer.DEFAULT_ROOT_CONFIG,
            ),
            resources=resources,
            tree_dir=sub_dir,
        )

    async def group_messages(
        self, messages: Iterable[MessageWithMusic]
    ) -> GroupedMessages:

        by_performer, no_performer = group_by_performer(
            filter(MessageWithMusic.guard, messages)
        )

        return by_performer, no_performer
