from typing import Any, Mapping, Type

from tgmount.cache import CacheFactoryMemory

from .provider_caches import CacheProviderBase
from .filters import (
    All,
    And,
    ByExtension,
    ByTypes,
    FilterProviderBase,
    FiltersMapping,
    First,
    Last,
    Not,
    OnlyUniqueDocs,
    Seq,
    Union,
    from_context_classifier,
)
from .provider_wrappers import DirWrappersProviderBase


class DirWrappersProvider(DirWrappersProviderBase):
    wrappers = {}


class CachesProvider(CacheProviderBase):
    caches = {
        "memory": CacheFactoryMemory,
    }


class VfsProducersProvider:
    @property
    def default(self):
        return None

    def get_producers(self) -> Mapping[str, Type[Any]]:
        return {}


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
