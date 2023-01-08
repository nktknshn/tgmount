import logging

import telethon

from tgmount.tgclient import TelegramFilesSource, TgmountTelegramClient
from tgmount.tgclient import guards
from tgmount.tgclient.client_types import TgmountTelegramClientReaderProto
from tgmount.tgclient.source.util import BLOCK_SIZE
from .types import CacheFactory

logger = logging.getLogger("tgmount-cache")
Message = telethon.tl.custom.Message


class FilesSourceCaching(TelegramFilesSource):
    """Caches telegram file content"""

    def __init__(
        self,
        client: TgmountTelegramClientReaderProto,
        cache_factory: CacheFactory,
        request_size: int = BLOCK_SIZE,
    ) -> None:
        self._cache_factory = cache_factory
        super().__init__(client, request_size)

    async def read(
        self,
        message: guards.MessageDownloadable,
        offset: int,
        limit: int,
    ) -> bytes:

        cache = await self._cache_factory.get_cache(message)

        data = await cache.read_range(
            lambda offset, limit, self=self: super(FilesSourceCaching, self).read(
                message, offset, limit
            ),
            offset,
            limit,
        )

        return data
