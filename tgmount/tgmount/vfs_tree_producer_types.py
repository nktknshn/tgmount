from dataclasses import dataclass
from typing import Optional, Iterable, Type, Protocol

from typing import Mapping
from abc import abstractmethod
from tgmount.tgclient import MessageSourceSubscribableProto
from tgmount.tgclient.message_types import MessageProto
from tgmount.tgmount.file_factory import FileFactoryProto
from tgmount.tgmount.filters_types import Filter
from tgmount.tgmount.types import MessagesSet, Set
from tgmount.tgmount.vfs_tree_wrapper_types import VfsTreeWrapperProto


class VfsTreeProducerProto(Protocol):
    @abstractmethod
    async def produce(self):
        ...

    @classmethod
    @abstractmethod
    async def from_config(
        cls,
        resources,
        config: "VfsTreeProducerConfig",
        arg: Mapping,
        dir,
        # dir: VfsTreeDir,
        # XXX
    ) -> "VfsTreeProducerProto":
        ...


class VfsTreeProducerConfig:
    """Wraps `message_source` with other"""

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
        self.message_source = message_source
        self.factory = factory
        self.filters = filters
        self.treat_as_prop = treat_as_prop

        self._messages: MessagesSet | None = None

    # async def on_update(self, source, messages):
    #     self._messages = await self._apply_all_filters(messages)

    async def produce_file(self, m: MessageProto):
        return self.factory.file(m, treat_as=self.treat_as_prop)

    async def apply_filters(self, messages: Iterable[MessageProto]) -> MessagesSet:
        for f in self.filters:
            messages = await f.filter(messages)

        return frozenset(messages)

    async def _apply_all_filters(self, input_messages: MessagesSet):
        # supported = await self.filter_supported(input_messages)
        filtered = await self.apply_filters(input_messages)
        return filtered

    async def filter_supported(
        self, input_messages: Iterable[MessageProto]
    ) -> MessagesSet:
        print(f"filter_supported")
        return self.factory.filter_supported(input_messages)

    async def get_messages(self) -> MessagesSet:
        """Get messages list from message_source, make set and apply filters"""
        messages = await self.message_source.get_messages()

        if self._messages is None:
            self._messages = await self._apply_all_filters(Set(messages))

        return self._messages

    def set_message_source(self, message_source: MessageSourceSubscribableProto):
        return VfsTreeProducerConfig(
            message_source=message_source,
            factory=self.factory,
            filters=self.filters,
            treat_as_prop=self.treat_as_prop,
        )


@dataclass
class VfsDirConfig:
    """Contains information for creating a `VfsProducer`"""

    source_config: Mapping
    """ Config this structure was sourced from """

    vfs_producer: Type[VfsTreeProducerProto] | None
    """ Producer for a vfs structure content """

    vfs_producer_arg: Optional[Mapping] = None
    """ Producer constructor argument """

    vfs_producer_config: Optional[VfsTreeProducerConfig] = None

    vfs_wrappers: Optional[
        list[tuple[Type[VfsTreeWrapperProto], Optional[Mapping]]]
    ] = None
    # vfs_wrapper_arg: Optional[Type[Mapping]] = None
