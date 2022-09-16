from abc import abstractmethod
from typing import Mapping, Protocol, TypeVar
from telethon.tl.custom.message import File, Message

from tgmount import tgclient
from tgmount.tgclient.message_source import Subscribable


MS = TypeVar("MS", bound=tgclient.MessageSourceSubscribableProto)


class SourcesProviderProto(Protocol[MS]):
    # def __init__(self) -> None:
    #     pass

    @abstractmethod
    def __getitem__(self, source_name: str) -> MS:
        ...

    @abstractmethod
    def get(self, source_name: str, default=None) -> MS | None:
        ...

    @abstractmethod
    def as_mapping(self) -> Mapping[str, MS]:
        ...


class SourcesProvider(SourcesProviderProto[MS]):
    def __init__(self, source_map: Mapping[str, MS]) -> None:
        self._source_map = source_map

    def __getitem__(self, source_name: str) -> MS:
        return self._source_map[source_name]

    def get(self, source_name: str, default=None) -> MS | None:
        return self._source_map.get(source_name, default)

    def as_mapping(self):
        return {**self._source_map}
