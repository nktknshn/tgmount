from dataclasses import dataclass, replace
from typing import Mapping, Type, Any

from tgmount.tgmount.file_factory import FileFactoryProto, ClassifierBase
from tgmount.tgmount.providers.provider_filters import FiltersMapping
from tgmount.tgmount.providers.provider_sources import SourcesProviderProto
from tgmount.tgmount.providers.provider_producers import ProducersProviderBase


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
    fetchers_dict: Mapping | None = None

    def set_sources(self, sources: SourcesProviderProto):
        return replace(self, sources=sources)
