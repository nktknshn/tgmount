import logging
import logging
import zipfile
from typing import Tuple

import greenback

from tgmount.vfs.types.file import FileContentProto
from tgmount.vfs.util import MyLock
from tgmount.zip.types import ZipFileAsyncThunk

FileContentZipHandle = Tuple[zipfile.ZipFile, zipfile.ZipExtFile]


logger = logging.getLogger("tgmount-zip")


class FileContentZip(FileContentProto):
    def __init__(self, z_factory: ZipFileAsyncThunk, zinfo: zipfile.ZipInfo):
        self.read_lock = MyLock(
            id=f"zipinfo_to_filelike({zinfo.filename})", logger=logger
        )
        self.zinfo = zinfo
        self.z_factory: ZipFileAsyncThunk = z_factory

        self._total_read = 0

    @property
    def size(self):
        return self.zinfo.file_size

    async def open_func(self) -> FileContentZipHandle:
        # XXX
        await greenback.ensure_portal()  # type: ignore

        logger.debug(f"zipinfo_to_filelike.open(zinfo.filename={self.zinfo.filename})")
        zf = await self.z_factory()

        async with self.read_lock:
            return zf, zf.open(self.zinfo)  # type: ignore

    async def read_func(self, handle: FileContentZipHandle, off, size):
        await greenback.ensure_portal()  # type: ignore

        logger.debug(f"zipinfo_to_filelike.read(off={off}, size={size})")
        zf, zext = handle

        async with self.read_lock:
            zext.seek(off)
            bs = zext.read(size)

            self._total_read += size

            return bs

    async def seek_func(self, handle: FileContentZipHandle, c, w=0):
        await greenback.ensure_portal()  # type: ignore

        zf, zext = handle
        logger.debug(f"zipinfo_to_filelike.seek(c={c}, w={w}")
        async with self.read_lock:
            zext.seek(c, w)

    async def close_func(self, handle: FileContentZipHandle):
        await greenback.ensure_portal()  # type: ignore

        zf, zext = handle
        logger.debug(f"zipinfo_to_filelike.close()")
        async with self.read_lock:
            zext.close()
            zf.close()

    async def tell_func(self, handle: FileContentZipHandle):
        await greenback.ensure_portal()  # type: ignore

        zf, zext = handle
        logger.debug(f"zipinfo_to_filelike.tell()")
        async with self.read_lock:
            return zext.tell()
