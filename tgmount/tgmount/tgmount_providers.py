from typing import Any, Mapping, Type

from tgmount.cache import CacheFactoryMemory
from tgmount.tgmount.producers.producer_by_performer import VfsTreeGroupByPerformer
from tgmount.tgmount.producers.producer_by_forward import VfsTreeGroupByForward
from tgmount.tgmount.producers.producer_by_sender import VfsTreeDirBySender
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
from .providers.provider_caches import CacheProviderBase
from .providers.provider_filters import FilterProviderBase, FiltersMapping
from .providers.provider_wrappers import DirWrappersProviderBase
from .providers.provider_producers import ProducersProviderBase


class DirWrappersProvider(DirWrappersProviderBase):
    wrappers = {}


class CachesProvider(CacheProviderBase):
    caches = {
        "memory": CacheFactoryMemory,  # type: ignore XXX
    }


class ProducersProvider(ProducersProviderBase):
    producers: Mapping[str, Type[VfsTreeProducerProto]] = {
        "PlainDir": VfsTreePlainDir,
        "BySender": VfsTreeDirBySender,
        "ByForward": VfsTreeGroupByForward,
        "ByPerformer": VfsTreeGroupByPerformer,
    }


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
