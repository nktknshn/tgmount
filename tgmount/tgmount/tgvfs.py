import errno
import logging
import os
import stat

import pyfuse3
from funcy import *

logvfs = logging.getLogger('tgvfs')


def message_doc_filename_format(msg, doc):
    attr_file_name = doc['attributes'].get('file_name')

    if attr_file_name:
        return ("%s %s" % (msg.id, attr_file_name)).encode()
    else:
        return ("msg_%s_doc" % msg.id).encode()


class TgfsFile(object):
    def __init__(self, msg, doc, inode=None, attr=None):
        self.inode = inode
        self.msg = msg
        self.doc = doc

        self.fname = message_doc_filename_format(msg, doc)
        self.attr = attr


class TelegramFsAsync(pyfuse3.Operations):
    def __init__(self, documents):
        super(TelegramFsAsync, self).__init__()

        self.documents = documents
        self.last_inode = pyfuse3.ROOT_INODE

        self.files = {}
        self.file_by_name = {}

        self.documents_to_files(documents)

    def update_index(self):
        self.file_by_name = walk_keys(
            lambda inode: self.files[inode].fname, self.files)

        self.inodes = list(self.files.keys())

    def documents_to_files(self, msg_documents):

        files = {}

        for msg in msg_documents:
            self._add_file(msg[0], msg[1])

        self.update_index()

    def add_file(self, msg, doc):
        self._add_file(msg, doc)
        self.update_index()

    def create_file(self, msg, doc, inode):

        attrs = pyfuse3.EntryAttributes()

        attrs.st_mode = (stat.S_IFREG | 0o644)
        attrs.st_size = doc.get('size')

        # What?

        stamp = int(doc['message_date'].timestamp() *
                    1e9) if 'message_date' in doc else int(1438467123.985654 * 1e9)
        attrs.st_atime_ns = stamp
        attrs.st_ctime_ns = stamp
        attrs.st_mtime_ns = stamp
        attrs.st_gid = os.getgid()
        attrs.st_uid = os.getuid()
        attrs.st_ino = inode

        file = TgfsFile(msg, doc, inode, attrs)

        return file

    def _add_file(self, msg, doc):
        inode = self.last_inode + 1
        self.files[inode] = self.create_file(msg, doc, inode)
        self.last_inode = inode

    async def getattr(self, inode, ctx=None):

        if inode == pyfuse3.ROOT_INODE:
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
        elif inode in self.files:
            return self.files[inode].attr
        else:
            raise pyfuse3.FUSEError(errno.ENOENT)

    async def lookup(self, parent_inode, name, ctx=None):
        logvfs.debug("lookup(%s,%s)" % (parent_inode, name))

        if parent_inode != pyfuse3.ROOT_INODE or name not in self.file_by_name:
            raise pyfuse3.FUSEError(errno.ENOENT)

        return self.file_by_name[name].attr

    async def opendir(self, inode, ctx):
        if inode != pyfuse3.ROOT_INODE:
            raise pyfuse3.FUSEError(errno.ENOENT)
        return inode

    async def readdir(self, fh, off, token):
        logvfs.debug("readdir(%s,%s)" % (fh, off))

        assert fh == pyfuse3.ROOT_INODE

        inodes = self.inodes[off:]

        for idx, inode in enumerate(inodes, off):
            file = self.files[inode]
            if not pyfuse3.readdir_reply(
                    token, file.fname, file.attr, idx + 1):
                break

    async def open(self, inode, flags, ctx):
        logvfs.info("open(%s)", self.files[inode].fname)

        if flags & os.O_RDWR or flags & os.O_WRONLY:
            logvfs.info("error: readonly")
            raise pyfuse3.FUSEError(errno.EPERM)

        # logvfs.info("ret %d", inode)
        return pyfuse3.FileInfo(fh=inode)

    async def read(self, fh, off, size):
        logvfs.debug("read(fh=%s,off=%s,size=%s). totoal: %s; " %
                     (fh, off, size, off + size))

        doc = self.files[fh].doc

        reading_func = doc['download_func']

        chunk = await reading_func(off, size)

        logvfs.debug("readurned: %s" % len(chunk))

        return chunk
