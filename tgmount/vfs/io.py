# every item should get inode
import logging
from typing import Any, Optional, IO

import greenback

from tgmount.vfs.types.file import FileContentProto

logger = logging.getLogger("tgmount-vfs")


class FileContentIO(IO[bytes]):
    def __init__(self, fc: FileContentProto, handle: Optional[Any] = None):
        super(FileContentIO, self).__init__()
        self.fc = fc
        self.pos = 0
        self.file_handle = handle

    async def read(self, n=-1):
        if n > -1:
            logger.debug(
                f"FileContentIO.read n={n}. pos={self.pos}. file_size={self.fc.size}"
            )
        else:
            logger.debug(
                f"FileContentIO.read n={n}. pos={self.pos}. file_size={self.fc.size}. will read {self.fc.size - self.tell()} bytes"
            )

        t = self.tell()
        n = n if n > -1 else (self.fc.size - t)

        ret = await self.fc.read_func(self.file_handle, t, n)

        if n > -1:
            self.pos += len(ret)
        else:
            self.pos = self.fc.size

        return ret

    async def seek(self, offset, whence=0):
        logger.debug(
            f"FileContentIO.seek offset={offset} whence={whence}. pos={self.pos}. size={self.fc.size}"
        )

        if whence == 0:
            new_pos = offset
        elif whence == 1:
            new_pos = self.pos + offset
        else:
            new_pos = self.fc.size + offset

        if new_pos > self.fc.size:
            new_pos = self.fc.size

        self.pos = new_pos

        if self.fc.seek_func:
            return await self.fc.seek_func(self.file_handle, offset, whence)

    async def close(self):
        logger.debug(f"FileContentIO.close()")
        if self.fc.close_func:
            return await self.fc.close_func(self.file_handle)

    async def tell(self):
        logger.debug(f"FileContentIO.tell()")
        if self.fc.tell_func:
            return await self.fc.tell_func(self.file_handle)

        return self.pos

    def seekable(self):
        return True


class FileContentIOGreenlet(FileContentIO):
    """Usable in synchronous code `IO[bytes]` implementation incapsulating async `FileContentProto` by means of `greenback` library"""

    def __init__(self, fc: FileContentProto, handle: Optional[Any] = None):
        super(FileContentIOGreenlet, self).__init__(fc, handle)

    def read(self, n=-1):
        return greenback.await_(super(FileContentIOGreenlet, self).read(n))

    def seek(self, offset, whence=0):
        return greenback.await_(super(FileContentIOGreenlet, self).seek(offset, whence))

    def close(self):
        return greenback.await_(super(FileContentIOGreenlet, self).close())

    def tell(self):
        return greenback.await_(super(FileContentIOGreenlet, self).tell())
