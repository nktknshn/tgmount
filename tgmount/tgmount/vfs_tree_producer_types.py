from dataclasses import dataclass
from typing import Optional, Iterable, Type, Protocol

from telethon.tl.custom import Message
from typing import Mapping
from abc import abstractmethod
from tgmount.tgclient import MessageSourceSubscribableProto
from tgmount.tgclient.message_source import Set
from tgmount.tgmount.file_factory import FileFactoryProto
from tgmount.tgmount.filters_types import Filter
from tgmount.tgmount.types import MessagesSet

# from .tgmount_types import TgmountResources
# from .vfs_tree import VfsTreeDir


class VfsTreeProducerProto(Protocol):
    @abstractmethod
    async def produce(self):
        ...

    @classmethod
    @abstractmethod
    async def from_config(
        cls,
        resources,
        config: "VfsStructureConfig",
        arg: Mapping,
        dir,
        # dir: VfsTreeDir,
        # XXX
    ) -> "VfsTreeProducerProto":
        ...


class ProducerConfig:
    message_source: MessageSourceSubscribableProto
    factory: FileFactoryProto
    filters: list[Filter]
    treat_as_prop: Optional[list[str]] = None

    def __init__(
        self,
        message_source: MessageSourceSubscribableProto,
        factory: FileFactoryProto,
        filters: list[Filter],
        treat_as_prop: Optional[list[str]] = None,
    ) -> None:
        # print("ProducerConfig")
        self.message_source = message_source
        self.factory = factory
        self.filters = filters
        self.treat_as_prop = treat_as_prop

        # self.message_source.subscribe(self.on_update)

        self._messages: MessagesSet | None = None

    # async def on_update(self, source, messages):
    #     self._messages = await self._apply_all_filters(messages)

    async def apply_filters(self, messages: Iterable[Message]) -> MessagesSet:
        for f in self.filters:
            messages = await f.filter(messages)

        return frozenset(messages)

    async def _apply_all_filters(self, input_messages: MessagesSet):
        # supported = await self.filter_supported(input_messages)
        filtered = await self.apply_filters(input_messages)
        return filtered

    async def filter_supported(self, input_messages: Iterable[Message]) -> MessagesSet:
        print(f"filter_supported")
        return self.factory.filter_supported(input_messages)

    async def get_messages(self) -> MessagesSet:
        """Get messages list from message_source, make set and apply filters"""
        messages = await self.message_source.get_messages()

        if self._messages is None:
            self._messages = await self._apply_all_filters(Set(messages))

        return self._messages

    def set_message_source(self, message_source: MessageSourceSubscribableProto):
        return ProducerConfig(
            message_source=message_source,
            factory=self.factory,
            filters=self.filters,
            treat_as_prop=self.treat_as_prop,
        )


@dataclass
class VfsStructureConfig:
    vfs_producer: Type[VfsTreeProducerProto] | None
    source_dict: Mapping
    vfs_producer_name: str | None = None
    vfs_producer_arg: Optional[dict] = None

    producer_config: Optional[ProducerConfig] = None