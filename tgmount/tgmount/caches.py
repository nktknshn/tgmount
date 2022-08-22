from typing import Type, Awaitable, Callable, Mapping
from tgmount.cache import CacheFactory, CacheFactoryMemory

from .types import CachesProviderProto, TgmountError


class CacheProviderBase(CachesProviderProto):
    caches: Mapping[str, Type[CacheFactory]]

    def get_caches(self) -> Mapping[str, Type[CacheFactory]]:
        return self.caches

    async def get_cache_factory(self, cache_type: str) -> Type[CacheFactory]:
        cache = self.get_caches().get(cache_type)

        if cache is None:
            raise TgmountError(f"Missing cache with type: {cache_type}")

        return cache
