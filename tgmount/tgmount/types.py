from dataclasses import dataclass, replace
from typing import (
    Any,
    Mapping,
    Type,
)

from tgmount import tg_vfs
from .filters import FiltersMapping
from .provider_sources import SourcesProviderProto

VfsProducersProviderProto = Any
@dataclass
class CreateRootResources:
    file_factory: tg_vfs.FileFactoryProto
    sources: SourcesProviderProto
    filters: FiltersMapping
    producers: VfsProducersProviderProto
    caches: Mapping[str, tg_vfs.FileFactoryProto]
    wrappers: Mapping[str, Type[Any]]
    vfs_wrappers: Mapping[str, Type[Any]]
    classifier: tg_vfs.ClassifierBase

    def set_sources(self, sources: SourcesProviderProto):
        return replace(self, sources=sources)

