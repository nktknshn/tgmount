from typing import Iterable

from telethon.tl.custom import Message

from tgmount import vfs
from tgmount import zip as z
from tgmount.cache import CacheFactoryMemory
from tgmount.tg_vfs.tree.helpers.remove_empty import remove_empty_dirs_content
from tgmount.tgclient import guards
from tgmount.util import col, func

from .caches import CacheProviderBase
from .filters import (
    All,
    ByExtension,
    ByTypes,
    Not,
    FilterProviderBase,
    First,
    Last,
    OnlyUniqueDocs,
    Union,
    Seq,
    from_guard,
)
from .wrappers import DirWrappersProviderBase, ExcludeEmptyDirs, ZipsAsDirsWrapper
from .producers import MessageBySender, TreeProducersProviderBase, MusicByPerformer


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


class TreeProducersProvider(TreeProducersProviderBase):
    producers = {
        "MusicByPerformer": MusicByPerformer,
        "MessageBySender": MessageBySender,
    }


class FilterProvider(FilterProviderBase):
    filters = {
        **{f.__name__: from_guard(f.guard) for f in ByTypes.guards},
        "OnlyUniqueDocs": OnlyUniqueDocs,
        "ByTypes": ByTypes,
        "All": All,
        "First": First,
        "Last": Last,
        "ByExtension": ByExtension,
        "Not": Not,
        "Union": Union,
        "Seq": Seq,
    }
