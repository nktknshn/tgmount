from typing import Protocol, Generic, TypeVar
import telethon


T = TypeVar("T", covariant=True)


class CacheFactoryProto(Protocol, Generic[T]):
    async def get_cache(
        self,
        message: telethon.tl.custom.Message,
    ) -> T:
        raise NotImplementedError()
