from typing import Iterable, Mapping, Type, TypeVar

from telethon.tl.custom import Message

from tgmount import vfs
from tgmount import zip as z
from tgmount import tgclient
from tgmount.cache import CacheFactoryMemory
from tgmount.tg_vfs.tree.helpers.remove_empty import remove_empty_dirs_content
from tgmount.tgclient import guards
from tgmount.tgmount.provider_sources import SourcesProviderProto
from tgmount.tgmount.vfs_structure_plain import VfsStructureProducerPlain
from .vfs_structure_producers_provider import VfsProducersProviderProto
from tgmount.util import col, func

from .caches import CacheProviderBase
from .filters import (
    All,
    And,
    ByExtension,
    ByTypes,
    FiltersMapping,
    Not,
    FilterProviderBase,
    First,
    Last,
    OnlyUniqueDocs,
    Union,
    Seq,
    from_context_classifier,
)
from .wrappers import DirWrappersProviderBase, ExcludeEmptyDirs, ZipsAsDirsWrapper
from .by_user import MessageByUser
from .vfs_structure_types import VfsStructureProducerProto
from .by_performer import MessageByPerformer

# async def zips_as_dirs(**kwargs) -> DirWrapper:
#     async def _inner(content: vfs.DirContentProto) -> vfs.DirContentProto:
#         return z.zips_as_dirs(content, **kwargs)

#     return _inner


class DirWrappersProvider(DirWrappersProviderBase):
    wrappers = {
        "ZipsAsDirs": ZipsAsDirsWrapper,
        "ExcludeEmptyDirs": ExcludeEmptyDirs,
        # "exclude_empty_dirs": lambda args: remove_empty_dirs_content,
    }


class CachesProvider(CacheProviderBase):
    caches = {
        "memory": CacheFactoryMemory,
    }


# class TreeProducersProvider(TreeProducersProviderBase):
#     producers = {
#         "MusicByPerformer": MusicByPerformer,
#         "MessageBySender": MessageBySender,
#         "MessageByForward": MessageByForwardSource,
#     }


class VfsProducersProvider(VfsProducersProviderProto):
    @property
    def default(self):
        return VfsStructureProducerPlain

    def get_producers(self) -> Mapping[str, Type[VfsStructureProducerProto]]:
        return {
            "MessageBySender": MessageByUser,
            "MusicByPerformer": MessageByPerformer,
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
