from typing import Protocol, Generic, TypeVar
import telethon

from tgmount.tg_vfs.source import SourceItem

T = TypeVar("T", covariant=True)


class CacheFactoryProto(Protocol, Generic[T]):
    async def get_cache(
        self,
        message: telethon.tl.custom.Message,
        document: SourceItem,
    ) -> T:
        raise NotImplementedError()
