from abc import abstractmethod
from typing import Mapping, Protocol, TypeVar

from tgmount import tgclient
from tgmount.util import none_fallback

MS = TypeVar(
    "MS",
    bound=tgclient.MessageSourceSubscribableProto,
    # covariant=True,
)


class SourcesProviderProto(Protocol[MS]):
    @abstractmethod
    def __getitem__(self, source_name: str) -> MS:
        ...

    @abstractmethod
    def get(self, source_name: str, default=None) -> MS | None:
        ...

    @abstractmethod
    def as_mapping(self) -> Mapping[str, MS]:
        ...

    @abstractmethod
    def add_source(self, source_id, source: MS):
        ...


class SourcesProvider(SourcesProviderProto[MS]):
    def __init__(self, source_map: dict[str, MS] | None = None) -> None:
        self._source_map: dict = none_fallback(source_map, {})

    def __getitem__(self, source_name: str) -> MS:
        return self._source_map[source_name]

    def get(self, source_name: str, default=None) -> MS | None:
        return self._source_map.get(source_name, default)

    def as_mapping(self) -> dict[str, MS]:
        return {**self._source_map}

    def add_source(self, source_id, source: MS):
        self._source_map[source_id] = source
