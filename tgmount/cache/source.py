import logging

import telethon

from tgmount.tgclient import TelegramFilesSource, TgmountTelegramClient
from tgmount.tgclient import guards
from tgmount.tgclient.client_types import TgmountTelegramClientReaderProto
from tgmount.tgclient.source.util import BLOCK_SIZE
from .types import CacheProto

logger = logging.getLogger("tgmount-cache")


class FilesSourceCached(TelegramFilesSource):
    """Caches telegram file content"""

    def __init__(
        self,
        client: TgmountTelegramClientReaderProto,
        cache: CacheProto,
        request_size: int = BLOCK_SIZE,
    ) -> None:
        super().__init__(client, request_size)
        self._cache = cache

    async def read(
        self,
        message: guards.MessageDownloadable,
        offset: int,
        limit: int,
    ) -> bytes:

        cache = await self._cache.get_reader(message)

        data = await cache.read_range(
            lambda offset, limit, self=self: super(FilesSourceCached, self).read(
                message, offset, limit
            ),
            offset,
            limit,
        )

        return data
