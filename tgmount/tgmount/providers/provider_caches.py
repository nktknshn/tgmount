from abc import abstractmethod
from typing import Protocol, Type, Mapping

from tgmount.cache import CacheInBlocksProto
from ..error import TgmountError


class CachesTypesProviderProto(Protocol):
    @abstractmethod
    def as_mapping(self) -> Mapping[str, Type[CacheInBlocksProto]]:
        pass

    @abstractmethod
    def get_cache_type(self, cache_type: str) -> Type[CacheInBlocksProto]:
        pass

    # @abstractmethod
    # async def create_cache_factory(self, cache_type: str, **kwargs) -> CacheFactory:
    #     pass


class CacheTypesProviderBase(CachesTypesProviderProto):
    caches: Mapping[str, Type[CacheInBlocksProto]]

    def as_mapping(self) -> Mapping[str, Type[CacheInBlocksProto]]:
        return self.caches

    def get_cache_type(self, cache_type: str) -> Type[CacheInBlocksProto]:
        cache = self.caches.get(cache_type)

        if cache is None:
            raise TgmountError(f"Missing cache with type: {cache_type}")

        return cache

    # async def create_cache_factory(self, cache_type: str, **kwargs) -> CacheFactory:
    #     ...
