from dataclasses import dataclass, replace
from typing import Mapping, Type, Any

from tgmount.tgmount.file_factory import FileFactoryProto, ClassifierBase
from tgmount.tgmount.provider_filters import FiltersMapping
from tgmount.tgmount.provider_sources import SourcesProviderProto
from tgmount.tgmount.provider_producers import ProducersProviderBase


@dataclass
class TgmountResources:
    file_factory: FileFactoryProto
    sources: SourcesProviderProto
    filters: FiltersMapping
    producers: ProducersProviderBase
    caches: Mapping[str, FileFactoryProto]
    wrappers: Mapping[str, Type[Any]]
    vfs_wrappers: Mapping[str, Type[Any]]
    classifier: ClassifierBase

    def set_sources(self, sources: SourcesProviderProto):
        return replace(self, sources=sources)
