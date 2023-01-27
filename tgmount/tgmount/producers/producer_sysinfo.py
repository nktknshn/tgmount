from typing import Any, Mapping
from tgmount import vfs
from tgmount.tgclient.guards import MessageDownloadable
from tgmount.tgmount.cached_filefactory_factory import CacheFileFactoryFactory
from tgmount.tgmount.tgmount_types import TgmountResources
from tgmount.tgmount.vfs_tree import VfsTreeDir
from tgmount.tgmount.vfs_tree_producer_types import (
    VfsTreeProducerConfig,
    VfsTreeProducerProto,
)
from tgmount.util import yes


def encode(s: str):
    return s.encode("utf-8")


class SysInfoFileCaches(vfs.FileContentBasic):
    """fuse doesn't support reading empty files like procfs"""

    size = 666666

    def __init__(self, caches: CacheFileFactoryFactory) -> None:
        self._caches = caches

    async def read(self, handle: Any) -> str:

        result = ""

        for cache_id in self._caches.ids:
            cache = self._caches.get_cache_by_id(cache_id)

            if not yes(cache):
                continue

            total_stored = await cache.total_stored()
            documents = cache.documents

            result += f"{cache_id}\n"
            result += f"Capacity\t{cache.capacity}\n"
            result += f"Block size\t{cache.block_size}\n"

            result += f"Total cached\t{total_stored} bytes\n"
            result += f"\n"

            result += f"chat_id\t\tmessage_id\tdocument_id\tfilename\tcached\n"

            for message, stored_bytes in await cache.stored_per_message():
                result += f"{message.chat_id}\t{message.id}\t{MessageDownloadable.document_or_photo_id(message)}\t{message.file.name}\t{stored_bytes} bytes\n"

            result += f"\n"

        return result


class VfsTreeProducerSysInfo(VfsTreeProducerProto):
    def __init__(
        self,
        resources: TgmountResources,
        vfs_tree_dir: VfsTreeDir,
    ) -> None:
        self._vfs_tree_dir = vfs_tree_dir
        self._resources = resources

    @classmethod
    async def from_config(
        cls,
        resources: TgmountResources,
        config: VfsTreeProducerConfig,
        arg: Mapping,
        vfs_tree_dir: VfsTreeDir,
    ) -> "VfsTreeProducerProto":
        return VfsTreeProducerSysInfo(
            resources=resources,
            vfs_tree_dir=vfs_tree_dir,
        )

    async def produce(self):
        await self._vfs_tree_dir.put_content(
            vfs.vfile("caches", SysInfoFileCaches(self._resources.caches)),
        )
