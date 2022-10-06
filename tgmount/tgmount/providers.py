from typing import Any, Mapping, Type

from tgmount.cache import CacheFactoryMemory
from tgmount.tgmount.producers.producer_by_user import VfsTreeDirByUser
from tgmount.tgmount.producers.producer_plain import VfsTreePlainDir
from tgmount.tgmount.vfs_tree_producer_types import VfsTreeProducerProto
from .filters import (
    All,
    And,
    ByExtension,
    First,
    Last,
    Not,
    OnlyUniqueDocs,
    Seq,
    Union,
    from_context_classifier,
)
from .provider_caches import CacheProviderBase
from .provider_filters import FilterProviderBase, FiltersMapping
from .provider_wrappers import DirWrappersProviderBase
from .provider_producers import ProducersProviderBase


class DirWrappersProvider(DirWrappersProviderBase):
    wrappers = {}


class CachesProvider(CacheProviderBase):
    caches = {
        "memory": CacheFactoryMemory,  # type: ignore XXX
    }


class ProducersProvider(ProducersProviderBase):
    producers: Mapping[str, Type[VfsTreeProducerProto]] = {
        "PlainDir": VfsTreePlainDir,
        "MessageBySender": VfsTreeDirByUser,
    }


# class VfsProducersProvider:
#     @property
#     def default(self):
#         return None

#     def get_producers(self) -> Mapping[str, Type[Any]]:
#         return {}


class FilterProvider(FilterProviderBase):
    filters = FiltersMapping(
        filters={
            "OnlyUniqueDocs": OnlyUniqueDocs,
            # "ByTypes": ByTypes,
            "All": All,
            "First": First,
            "Last": Last,
            "ByExtension": ByExtension,
            "Not": Not,
            "Union": Union,
            "Seq": Seq,
            "And": And,
        },
        filter_getters=[
            from_context_classifier,
        ],
    )
