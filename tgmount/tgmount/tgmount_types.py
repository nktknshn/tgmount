from dataclasses import dataclass, replace
from typing import Mapping, Type, Any

from tgmount.tgmount.file_factory import FileFactoryProto, ClassifierBase
from tgmount.tgmount.providers.provider_filters import (
    FilterProviderProto,
)
from tgmount.tgmount.providers.provider_sources import SourcesProviderProto
from tgmount.tgmount.providers.provider_producers import ProducersProviderBase
from tgmount.tgmount.providers.provider_vfs_wrappers import ProviderVfsWrappersBase

# from tgmount.tgmount.providers.provider_producers import ProducersProviderBase


@dataclass
class TgmountResources:
    """Stores resourses which are used for producing VfsTree from a config"""

    file_factory: FileFactoryProto
    sources: SourcesProviderProto
    filters: FilterProviderProto
    producers: ProducersProviderBase
    caches: Mapping[str, FileFactoryProto]
    vfs_wrappers: ProviderVfsWrappersBase
    classifier: ClassifierBase

    fetchers_dict: Mapping | None = None
    """ Dictionary of initial messages fetchers """

    def set_sources(self, sources: SourcesProviderProto):
        return replace(self, sources=sources)
