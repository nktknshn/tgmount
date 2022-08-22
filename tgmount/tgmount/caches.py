from typing import Type, Awaitable, Callable, Mapping
from tgmount.cache import CacheFactory, CacheFactoryMemory

from .types import CachesProviderProto, TgmountError


class CacheProvider(CachesProviderProto):
    def __init__(self) -> None:
        super().__init__()

    def get_caches(self) -> Mapping[str, Type[CacheFactory]]:
        return {
            "memory": CacheFactoryMemory,
        }

    async def get_cache_factory(self, cache_type: str) -> Type[CacheFactory]:
        cache = self.get_caches().get(cache_type)

        if cache is None:
            raise TgmountError(f"Missing cache with type: {cache_type}")

        return cache
