from typing import Iterable

from telethon.tl.custom import Message

from tgmount import vfs
from tgmount import zip as z
from tgmount.cache import CacheFactoryMemory
from tgmount.tgclient import guards
from tgmount.util import col, func

from .caches import CacheProviderBase
from .filters import (
    All,
    ByTypes,
    FilterProviderBase,
    First,
    Last,
    OnlyUniqueDocs,
    from_guard,
)
from .types import DirWrapper, FilterAllMessagesProto
from .wrappers import DirWrappersProviderBase


async def zips_as_dirs(**kwargs) -> DirWrapper:
    async def _inner(content: vfs.DirContentProto) -> vfs.DirContentProto:
        return z.zips_as_dirs(content, **kwargs)

    return _inner


class DirWrappersProvider(DirWrappersProviderBase):
    wrappers = {
        "zips_as_dirs": zips_as_dirs,
    }


class CachesProvider(CacheProviderBase):
    caches = {
        "memory": CacheFactoryMemory,
    }


class FilterProvider(FilterProviderBase):
    filters = {
        **{f.__name__: from_guard(f.guard) for f in ByTypes.guards},
        "OnlyUniqueDocs": OnlyUniqueDocs,
        "ByTypes": ByTypes,
        "All": All,
        "First": First,
        "Last": Last,
    }
