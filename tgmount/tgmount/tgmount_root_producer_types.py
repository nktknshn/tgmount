from dataclasses import dataclass, field, make_dataclass, replace
from typing import Any, Iterable, Optional, Protocol, Type, TypedDict, TypeVar, Mapping

from telethon.tl.custom import Message

from tgmount import config, tg_vfs, tgclient, vfs
from tgmount.tg_vfs import FileFactoryProto
from tgmount.tg_vfs.tree.message_tree import create_dir_content_source
from tgmount.tgclient.guards import MessageDownloadable
from tgmount.tgclient.message_source import (
    MessageSourceSubscribableProto,
    MessageSourceProto,
)
from tgmount.tgmount.vfs_wrappers import VfsWrapperProto
from tgmount.util import col, is_not_none, none_fallback

from .filters import Filter
from .logger import logger
from .util import to_list_of_single_key_dicts

from .vfs_structure_types import VfsStructureProducerProto
from .types import CreateRootResources

Set = frozenset
MessagesSet = frozenset[Message]
TgmountRootSource = dict
MessageTuple = tuple[int, int | None]


ProducedContentMapping = dict[
    tgclient.MessageSourceProto, dict[str, "ProducedDirContent"]
]


def message_to_tuple(m: Message) -> MessageTuple:
    return (m.id, MessageDownloadable.try_document_or_photo_id(m))


def messages_to_tuples(ms: Iterable[Message]) -> Set[MessageTuple]:
    return Set(map(message_to_tuple, ms))


def messages_to_tuples_set(ms: Iterable[Message]) -> Set[MessageTuple]:
    return Set(map(message_to_tuple, ms))


@dataclass
class ProducedDirContent:
    producer_config: "ProducerConfig"
    supported_source_messages_set: Set[MessageTuple]
    filtered_source_messages_set: Set[MessageTuple]
    result_content: vfs.DirContentProto


@dataclass
class ProducerConfig:
    message_source: MessageSourceSubscribableProto
    factory: FileFactoryProto
    filters: list[Filter]
    treat_as_prop: Optional[list[str]] = None

    async def apply_filters(self, messages: MessagesSet) -> MessagesSet:
        for f in self.filters:
            messages = await f.filter(messages)

        return frozenset(messages)

    async def apply_all_filters(self, input_messages: Iterable[Message]):
        supported = await self.filter_supported(input_messages)
        filtered = await self.apply_filters(supported)
        return filtered

    async def filter_supported(self, input_messages: Iterable[Message]) -> MessagesSet:
        return self.factory.filter_supported(input_messages)

    async def get_messages(self) -> MessagesSet:
        messages = await self.message_source.get_messages()
        return await self.apply_all_filters(messages)

    def set_message_source(self, message_source: MessageSourceSubscribableProto):
        return replace(self, message_source=message_source)


@dataclass
class VfsStructureConfig:
    vfs_producer: Type[VfsStructureProducerProto]
    source_dict: dict
    vfs_producer_name: str | None = None
    vfs_producer_arg: Optional[dict] = None
    vfs_wrappers: list[VfsWrapperProto] = field(default_factory=list)

    producer_config: Optional[ProducerConfig] = None


@dataclass
class CreateRootContext:
    """Immutable context to traverse root config dictionary"""

    current_path: list[str]
    file_factory: FileFactoryProto
    classifier: tg_vfs.ClassifierBase
    recursive_source: Optional[MessageSourceSubscribableProto] = None
    recursive_filters: Optional[list[Filter]] = None

    def set_recursive_source(self, source: Optional[MessageSourceProto]):
        return replace(self, recursive_source=source)

    def set_recursive_filters(self, recursive_filters: Optional[list[Filter]]):
        return replace(self, recursive_filters=recursive_filters)

    def extend_recursive_filters(self, filters: list[Filter]):
        return replace(
            self,
            recursive_filters=[*none_fallback(self.recursive_filters, []), *filters],
        )

    def set_file_factory(self, file_factory: FileFactoryProto):
        return replace(self, file_factory=file_factory)

    def add_path(self, element: str):
        return replace(self, current_path=[*self.current_path, element])

    def set_path(self, path: list[str]):
        return replace(self, current_path=path)

    @staticmethod
    def from_resources(
        resources: CreateRootResources,
        current_path: list[str] | None = None,
        recursive_source: Optional[MessageSourceSubscribableProto] = None,
    ):
        return CreateRootContext(
            current_path=none_fallback(current_path, []),
            recursive_source=recursive_source,
            file_factory=resources.file_factory,
            classifier=resources.classifier,
        )
