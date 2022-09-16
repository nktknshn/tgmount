from abc import abstractmethod, abstractstaticmethod
import os
from collections.abc import Awaitable, Callable
import telethon
from typing import Iterable, Optional, Protocol, TypeVar
from telethon.tl.custom import Message
from tgmount.tg_vfs.types import FileFactoryProto
from tgmount.tgclient.message_source import (
    MessageSourceProto,
    MessageSourceSubscribable,
    MessageSourceSubscribableProto,
    Subscribable,
)
from tgmount.tgmount.error import TgmountError
from tgmount.tgmount.filters import Filter
from tgmount.tgmount.vfs_wrappers import VfsWrapperProto

from tgmount.util import none_fallback


from tgmount import vfs, tglog, fs

from .tgmount_root_producer_types import (
    CreateRootContext,
    ProducerConfig,
    MessagesSet,
    Set,
    TgmountRootSource,
    VfsStructureConfig,
)
from .types import CreateRootResources
from .tgmount_root_config_reader import TgmountConfigReader
from .vfs_structure_types import FsUpdate, VfsStructureProducerProto, VfsStructureProto
from .vfs_structure import VfsStructure

logger = tglog.getLogger("VfsStructure")
logger.setLevel(tglog.TRACE)

T = TypeVar("T")


def sets_difference(left: Set[T], right: Set[T]) -> tuple[Set[T], Set[T], Set[T]]:
    unique_left = left - right
    unique_right = right - left
    common = right.intersection(left)

    return unique_left, unique_right, common


class VfsStructureProducerEmpty(VfsStructureProducerProto):
    def __init__(self, *args) -> None:
        self._vfs_structure = VfsStructure()

    def get_vfs_structure(self) -> VfsStructureProto:
        return self._vfs_structure

    async def produce_vfs_struct(
        self,
    ) -> VfsStructure:
        return VfsStructure()

    @staticmethod
    def from_config(resources, *args) -> "VfsStructureProducerProto":
        return VfsStructureProducerEmpty()


class VfsStructureProducerPlain(VfsStructureProducerProto):
    """
    Simple dir content producer
    Takes message_source, factory and filters and produces VfsStructure made of a single DirContent
    storing FileLikes
    Watches message source updates and updates the produced VfsStructure
    """

    def __repr__(self) -> str:
        return f"VfsStructureProducerPlain(root_producer={self._root_producer}, tag={self._tag})"

    @staticmethod
    def create(
        root_producer: Optional[VfsStructureProducerProto],
        message_source: MessageSourceSubscribable,
        factory: FileFactoryProto,
        filters: list[Filter] | None = None,
        tag: str | None = None,
    ):
        return VfsStructureProducerPlain(
            ProducerConfig(
                message_source=message_source,
                factory=factory,
                filters=none_fallback(filters, []),
            ),
            root_producer,
            tag,
        )

    def __init__(
        self,
        producer_cfg: ProducerConfig,
        root_producer: VfsStructureProducerProto | None = None,
        tag: str | None = None,
    ) -> None:
        super().__init__()

        self._producer_cfg = producer_cfg
        self._messages: Optional[MessagesSet] = None
        self._vfs_structure: Optional[VfsStructure] = None

        self._message_to_file: dict[Message, vfs.FileLike] = {}

        self._logger = tglog.getLogger("VfsStructureProducerPlain")
        self._root_producer = root_producer
        self._tag = tag

    def get_vfs_structure(self) -> VfsStructureProto:
        if self._vfs_structure is None:
            raise TgmountError(f"_vfs_structure is None")

        return self._vfs_structure

    async def produce_vfs_struct(
        self,
    ) -> VfsStructure:
        self._logger.info(f"produce_vfs_struct")

        self._vfs_structure = VfsStructure()

        messages = await self._producer_cfg.message_source.get_messages()

        self._messages = messages = await self._producer_cfg.apply_all_filters(messages)
        self._message_to_file = {
            m: self._producer_cfg.factory.file(m) for m in messages
        }

        self._logger.info(
            f"produce_vfs_struct: {len(self._message_to_file.values())} files"
        )

        await self._vfs_structure.put("/", list(self._message_to_file.values()))

        self._producer_cfg.message_source.subscribe(self.on_message_source_update)

        return self._vfs_structure

    async def on_message_source_update(
        self,
        source,
        messages: list[Message],
    ):
        # self._logger.info(f"on_update")

        if self._messages is None or self._vfs_structure is None:
            self._logger.error(f"missing cached messages or vfs_structure")
            return

        messages_set = await self._producer_cfg.apply_all_filters(messages)

        removed_messages, new_messages, common_messages = sets_difference(
            self._messages, messages_set
        )

        removed_files = [self._message_to_file[m] for m in removed_messages]
        old_files = [self._message_to_file[m] for m in common_messages]
        new_files = [self._producer_cfg.factory.file(m) for m in new_messages]

        self._messages = messages_set
        self._message_to_file = {
            **{m: f for m, f in zip(new_messages, new_files)},
            **{m: f for m, f in zip(common_messages, old_files)},
        }

        for f in removed_files:
            await self._vfs_structure.remove_by_path(f.name)

        for f in new_files:
            await self._vfs_structure.put("/", [f])

        if (
            len(removed_files) > 0 or len(new_files) > 0
        ) and self._root_producer is not None:
            await self._root_producer.on_child_update(
                self,
                FsUpdate(
                    update_dir_content=["/"],
                    details=dict(
                        removed_files=[f.name for f in removed_files],
                        new_files={f.name: f for f in new_files},
                    ),
                ),
            )

    @staticmethod
    def from_config(
        root_producer: "VfsStructureProducerProto",
        resources,
        cfg: VfsStructureConfig,
        arg,
    ) -> "VfsStructureProducerProto":

        if cfg.producer_config is None:
            return VfsStructureProducerEmpty(root_producer)
        else:
            return VfsStructureProducerPlain(cfg.producer_config, root_producer)
