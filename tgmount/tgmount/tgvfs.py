import errno
import logging
import os
import stat
import traceback
from typing import Dict

import pyfuse3
from funcy import *

from tgmount.dclasses import TgmountDocument, DocumentHandle, TgfsFile
from telethon.tl.custom import Message

logvfs = logging.getLogger('tgvfs')


def create_attributes(
        inode: int,
        size: int = 0,
        directory: bool = True,
        stamp: int = int(1438467123.985654 * 1e9)):
    attrs = pyfuse3.EntryAttributes()

    if not directory:
        attrs.st_mode = (stat.S_IFREG | 0o644)
    else:
        attrs.st_mode = (stat.S_IFDIR | 0o755)

    attrs.st_size = size

    stamp = stamp

    attrs.st_atime_ns = stamp
    attrs.st_ctime_ns = stamp
    attrs.st_mtime_ns = stamp
    attrs.st_gid = os.getgid()
    attrs.st_uid = os.getuid()
    attrs.st_ino = inode

    return attrs


def create_attributes_from_doc(doc: TgmountDocument, inode: int):
    attrs = create_attributes(
        inode=inode,
        size=doc.size,
        stamp=int(doc.message_date.timestamp() * 1e9) if doc.message_date else int(1438467123.985654 * 1e9),
        directory=False
    )

    return attrs


def root_attr():
    entry = pyfuse3.EntryAttributes()
    entry.st_mode = (stat.S_IFDIR | 0o755)
    entry.st_size = 0
    stamp = int(1438467123.985654 * 1e9)
    entry.st_atime_ns = stamp
    entry.st_ctime_ns = stamp
    entry.st_mtime_ns = stamp
    entry.st_gid = os.getgid()
    entry.st_uid = os.getuid()
    entry.st_ino = pyfuse3.ROOT_INODE

    return entry


def exception_handler(func):
    async def inner_function(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except pyfuse3.FUSEError:
            raise
        except Exception:
            logvfs.error(traceback.format_exc())
            raise pyfuse3.FUSEError(errno.EIO)

    return inner_function


class TelegramFsAsync(pyfuse3.Operations):
    def __init__(self):
        super(TelegramFsAsync, self).__init__()

        self._files: Dict[int, TgfsFile] = {}
        self._file_by_name = {}

        self._inodes = []
        self._last_inode = pyfuse3.ROOT_INODE

    def update_index(self):
        self._file_by_name = walk_keys(
            lambda inode: self._files[inode].fname, self._files)

        self._inodes = list(self._files.keys())

    def add_file(self, msg: Message, doc: DocumentHandle, update_index=True) -> TgfsFile:
        inode = self._last_inode + 1

        attrs = create_attributes_from_doc(doc.document, inode)
        new_file = TgfsFile(msg, doc, inode, attrs)

        self._files[inode] = new_file
        self._last_inode = inode

        if update_index:
            self.update_index()

        return new_file

    @exception_handler
    async def getattr(self, inode: int, ctx=None):
        if inode == pyfuse3.ROOT_INODE:
            return root_attr()
        elif inode in self._files:
            return self._files[inode].attr
        else:
            raise pyfuse3.FUSEError(errno.ENOENT)

    @exception_handler
    async def lookup(self, parent_inode: int, name: str, ctx=None):
        logvfs.debug("lookup(%s,%s)" % (parent_inode, name))

        if parent_inode != pyfuse3.ROOT_INODE or name not in self._file_by_name:
            raise pyfuse3.FUSEError(errno.ENOENT)

        return self._file_by_name[name].attr

    @exception_handler
    async def releasedir(self, fh):
        logvfs.debug("releasedir(%s)" % fh)

    @exception_handler
    async def opendir(self, inode, ctx):
        logvfs.debug("opendir(%s,%s)" % (inode, ctx))
        if inode != pyfuse3.ROOT_INODE:
            raise pyfuse3.FUSEError(errno.ENOENT)
        return inode

    @exception_handler
    async def readdir(self, fh, off, token):
        logvfs.debug("readdir(%s,%s)" % (fh, off))

        assert fh == pyfuse3.ROOT_INODE

        inodes = self._inodes[off:]

        for idx, inode in enumerate(inodes, off):
            file = self._files[inode]
            if not pyfuse3.readdir_reply(
                    token, file.fname, file.attr, idx + 1):
                break

    @exception_handler
    async def open(self, inode, flags, ctx):

        if inode not in self._files:
            raise pyfuse3.FUSEError(errno.ENOENT)

        logvfs.info("open(%s)", self._files[inode].fname)

        if flags & os.O_RDWR or flags & os.O_WRONLY:
            logvfs.info("error: readonly")
            raise pyfuse3.FUSEError(errno.EPERM)

        return pyfuse3.FileInfo(fh=inode)

    @exception_handler
    async def read(self, fh, off, size):
        logvfs.debug("read(fh=%s,off=%s,size=%s). total: %s; " %
                     (fh, off, size, off + size))

        dh = self._files[fh].handle
        chunk = await dh.read_func(off, size)
        logvfs.debug("readurned: %s" % len(chunk))

        return chunk
