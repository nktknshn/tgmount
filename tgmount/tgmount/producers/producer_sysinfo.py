from typing import Any, Mapping
from tgmount import vfs
from tgmount.tgmount.tgmount_types import TgmountResources
from tgmount.tgmount.vfs_tree import VfsTreeDir
from tgmount.tgmount.vfs_tree_producer_types import (
    VfsTreeProducerConfig,
    VfsTreeProducerProto,
)


class SysInfoFileContentInfo(vfs.FileContentProto):
    size = 0

    async def read_func(self, handle: Any, off: int, size: int) -> bytes:
        return "file info".encode("utf-8")


class VfsTreeProducerSysInfo(VfsTreeProducerProto):
    def __init__(self, vfs_tree_dir: VfsTreeDir) -> None:
        self._vfs_tree_dir = vfs_tree_dir

    @classmethod
    async def from_config(
        cls,
        resources: TgmountResources,
        config: VfsTreeProducerConfig,
        arg: Mapping,
        vfs_tree_dir: VfsTreeDir,
    ) -> "VfsTreeProducerProto":
        return VfsTreeProducerSysInfo(vfs_tree_dir=vfs_tree_dir)

    async def produce(self):
        await self._vfs_tree_dir.put_content(
            vfs.vfile("info", SysInfoFileContentInfo()),
        )
