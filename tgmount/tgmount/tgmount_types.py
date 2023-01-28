from dataclasses import dataclass, replace
from typing import Mapping, Type, Any
from tgmount.config.types import MessageSource
from tgmount.tgclient.message_source_types import (
    MessageSourceProto,
    MessageSourceProto,
)
from tgmount.tgclient.message_types import MessageProto
from tgmount.tgmount.cached_filefactory_factory import CacheFileFactoryFactory

from tgmount.tgmount.file_factory import FileFactoryProto, ClassifierBase
from tgmount.tgmount.providers.provider_caches import CachesTypesProviderProto
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
    classifier: ClassifierBase
    message_sources: SourcesProviderProto[MessageSourceProto[MessageProto]]
    filters: FilterProviderProto
    producers: ProducersProviderBase
    caches: CacheFileFactoryFactory
    vfs_wrappers: ProviderVfsWrappersBase

    fetchers_dict: Mapping
    #  | None = None
    """ Dictionary of initial messages fetchers """

    extra: Mapping[str, Any]

    def set_sources(self, sources: SourcesProviderProto):
        return replace(self, sources=sources)

    def set_factory(self, file_factory: FileFactoryProto):
        return replace(self, file_factory=file_factory)
