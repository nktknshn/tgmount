import io
import logging
import os
import zipfile
from typing import IO, Callable, Tuple

import greenback
from tgmount.vfs.file import FileContent, FileLike
from tgmount.vfs.types.file import FileContentProto
from tgmount.vfs.util import MyLock
from tgmount.zip.types import ZipFileAsyncThunk

ZipFileHandle = Tuple[zipfile.ZipFile, zipfile.ZipExtFile]


logger = logging.getLogger("tgmount-zip")

""" 
class FileContentImpl:
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

    async def open(self) -> ZipFileHandle2:
        # XXX
        await greenback.ensure_portal()  # type: ignore

        logger.debug(f"zipinfo_to_filelike.open(zinfo.filename={self.zinfo.filename})")
        fh, zf = await self.z_factory()

        async with self.read_lock:
            return zf, zf.open(self.zinfo)  # type: ignore

    async def read(self, handle: ZipFileHandle2, off, size):
        await greenback.ensure_portal()  # type: ignore

        logger.debug(f"zipinfo_to_filelike.read(off={off}, size={size})")
        zf, zext = handle

        async with self.read_lock:
            zext.seek(off)
            bs = zext.read(size)

            self._total_read += size

            return bs

    async def seek(self, handle: ZipFileHandle2, c, w=0):
        await greenback.ensure_portal()  # type: ignore

        zf, zext = handle
        logger.debug(f"zipinfo_to_filelike.seek(c={c}, w={w}")
        async with self.read_lock:
            zext.seek(c, w)

    async def close(self, handle: ZipFileHandle2):
        await greenback.ensure_portal()  # type: ignore

        zf, zext = handle
        logger.debug(f"zipinfo_to_filelike.close()")
        async with self.read_lock:
            zext.close()
            zf.close()

    async def tell(self, handle: ZipFileHandle2):
        await greenback.ensure_portal()  # type: ignore

        zf, zext = handle
        logger.debug(f"zipinfo_to_filelike.tell()")
        async with self.read_lock:
            return zext.tell()
 """


def create_file_content_from_zipinfo(
    z_factory: ZipFileAsyncThunk, zinfo: zipfile.ZipInfo
) -> FileContentProto:

    return FileContentZip(z_factory, zinfo)


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

    async def open_func(self) -> ZipFileHandle:
        # XXX
        await greenback.ensure_portal()  # type: ignore

        logger.debug(f"zipinfo_to_filelike.open(zinfo.filename={self.zinfo.filename})")
        fh, zf = await self.z_factory()

        async with self.read_lock:
            return zf, zf.open(self.zinfo)  # type: ignore

    async def read_func(self, handle: ZipFileHandle, off, size):
        await greenback.ensure_portal()  # type: ignore

        logger.debug(f"zipinfo_to_filelike.read(off={off}, size={size})")
        zf, zext = handle

        async with self.read_lock:
            zext.seek(off)
            bs = zext.read(size)

            self._total_read += size

            return bs

    async def seek_func(self, handle: ZipFileHandle, c, w=0):
        await greenback.ensure_portal()  # type: ignore

        zf, zext = handle
        logger.debug(f"zipinfo_to_filelike.seek(c={c}, w={w}")
        async with self.read_lock:
            zext.seek(c, w)

    async def close_func(self, handle: ZipFileHandle):
        await greenback.ensure_portal()  # type: ignore

        zf, zext = handle
        logger.debug(f"zipinfo_to_filelike.close()")
        async with self.read_lock:
            zext.close()
            zf.close()

    async def tell_func(self, handle: ZipFileHandle):
        await greenback.ensure_portal()  # type: ignore

        zf, zext = handle
        logger.debug(f"zipinfo_to_filelike.tell()")
        async with self.read_lock:
            return zext.tell()
