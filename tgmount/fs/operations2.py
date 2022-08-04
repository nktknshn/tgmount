import errno
import logging
import os
import time
from dataclasses import dataclass

import pyfuse3
from tgmount.fs.fh import FileSystemHandlers
from tgmount.fs.inode2 import InodesRegistry, RegistryItem, RegistryRoot
from tgmount.fs.types import OpendirContext
from tgmount.fs.util import (
    create_directory_attributes,
    create_file_attributes,
    exception_handler,
)
from tgmount.vfs import DirContentItem, DirLike, FileLike

# XXX
# try:
#     import faulthandler
# except ImportError:
#     pass
# else:
#     faulthandler.enable()

logger = logging.getLogger("tgvfs-ops")


@dataclass
class FileSystemItem:
    structure_item: DirContentItem
    attrs: pyfuse3.EntryAttributes


InodesRegistryItem = RegistryItem[FileSystemItem] | RegistryRoot[FileSystemItem]


class FileSystemOperations(pyfuse3.Operations):
    def __init__(
        self,
        root: DirLike,
        # mount_point: str,
        # context_factory
    ):
        super(FileSystemOperations, self).__init__()

        # self._mount_point = mount_point
        self._inodes = InodesRegistry[FileSystemItem](
            self.create_FileSystemItem(
                root,
                self._create_attributes_for_item(root, InodesRegistry.ROOT_INODE),
            )
        )
        self._handlers = FileSystemHandlers[InodesRegistryItem]()

    def _str_to_bytes(self, s: str) -> bytes:
        return s.encode("utf-8")

    def create_FileSystemItem(
        self,
        structure_item: DirContentItem,
        attrs: pyfuse3.EntryAttributes,
    ):
        return FileSystemItem(structure_item, attrs)

    def _create_attributes_for_item(
        self,
        item: DirContentItem,
        inode: int,
    ):
        if isinstance(item, DirLike):
            return create_directory_attributes(
                inode,
                stamp=int(item.creation_time.timestamp() * 1e9),
            )
        else:
            return create_file_attributes(
                size=item.content.size,
                stamp=int(item.creation_time.timestamp() * 1e9),
            )

    @exception_handler
    async def getattr(self, inode: int, ctx=None):
        logger.debug(f"= getattr({inode},)")
        item = self._inodes.get_item_by_inode(inode)

        if item is None:
            logger.error(f"= getattr({inode}): missing in inodes registry")
            raise pyfuse3.FUSEError(errno.ENOENT)

        logger.debug(f"= getattr({inode},)\t{item.data.structure_item.name}")

        return item.data.attrs

    @exception_handler
    async def _read_dir_content(self, parent_item: InodesRegistryItem):
        logger.debug("registering folder")

        handle = None
        structure_item = parent_item.data.structure_item

        if not isinstance(structure_item, DirLike):
            logger.error("_read_content(): parent_item is not DirLike")
            raise pyfuse3.FUSEError(errno.ENOENT)

        handle = await structure_item.content.opendir_func()
        res = []

        for child_item in await structure_item.content.readdir_func(handle, 0):
            item = self._inodes.add_item_to_inodes(
                self._str_to_bytes(child_item.name),
                self.create_FileSystemItem(
                    child_item,
                    self._create_attributes_for_item(child_item, inode=0),
                ),
                parent_inode=parent_item.inode,
            )
            item.data.attrs.st_ino = item.inode
            res.append(item)

        await structure_item.content.releasedir_func(handle)

        return res

    @exception_handler
    async def lookup(
        self, parent_inode: int, name: bytes, ctx=None
    ) -> pyfuse3.EntryAttributes:
        # Calls to lookup acquire a read-lock on the inode of the parent directory (meaning that lookups in the same
        #         directory may run concurrently, but never at the same time as e.g. a rename or mkdir operation).

        logger.debug(f"= lookup({parent_inode}, {name})")

        parent_item = self._inodes.get_item_by_inode(parent_inode)

        if parent_item is None:
            logger.error(f"lookup({parent_inode}): missing parent_inode={parent_inode}")
            raise pyfuse3.FUSEError(errno.ENOENT)

        logger.debug(f"lookup(): parent_item={parent_item.name}")

        if not DirLike.guard(parent_item.data.structure_item):
            logger.error("lookup(): parent_item is not DirLike")
            raise pyfuse3.FUSEError(errno.ENOENT)

        child_inodes = self._inodes.get_items_by_parent(parent_inode)

        # XXX
        if child_inodes == []:
            await self._read_dir_content(parent_item)

        item = self._inodes.get_child_item_by_name(name, parent_inode)

        if item is None:
            logger.error(f"lookup(parent_inode={parent_inode},name={name}): not found")
            raise pyfuse3.FUSEError(errno.ENOENT)

        logger.debug(f"lookup(): returning {item}")

        return item.data.attrs

    @exception_handler
    async def forget(self, inode_list):
        logger.info("f= forget({inode_list}")

    @exception_handler
    async def opendir(self, inode: int, ctx):
        logger.debug("f= opendir({inode}")

        item = self._inodes.get_item_by_inode(inode)

        if item is None:
            logger.error(f"opendir({inode}): missing item")
            raise pyfuse3.FUSEError(errno.EBADF)

        logger.debug(f"= opendir({inode}) {item.data.structure_item.name}")

        structure_item = item.data.structure_item

        if not DirLike.guard(item.data.structure_item):
            logger.error(f"opendir({inode}): structure_item is not DirLike")
            raise pyfuse3.FUSEError(errno.ENOTDIR)

        # if item.structure_item.content is None:
        #     logger.error('missing item.structure_item.content')
        #     return

        path = self._inodes.get_path(item.inode)

        if path is not None:
            vfs_path = InodesRegistry.join_path(path)

            if vfs_path is None:
                logger.error("opendir(): missing vfs_path")
                raise pyfuse3.FUSEError(errno.ENOENT)

            logger.debug(f"opendir(): vfs_path = {vfs_path}")

        # opendir_context = OpendirContext(
        #     vfs_path=vfs_path, full_path=os.path.join(self._mount_point, vfs_path)
        # )

        # logger.debug('opendir(): opendir_context = %s', opendir_context)
        # opendir_context

        handle = await item.data.structure_item.content.opendir_func()

        fh = self._handlers.open_fh(item, handle)

        logger.debug(f"opendir({inode}) = {fh}")
        return fh

    @exception_handler
    async def readdir(self, fh, off, token: pyfuse3.ReaddirToken):
        logger.debug(f"= readdir(fh={fh}, off={off})")

        parent_item, handle = self._handlers.get_by_fh(fh)

        if parent_item is None:
            logger.error("= readdir(fh={fh}, off={off}): missing parent_item")
            raise pyfuse3.FUSEError()

        content = self._inodes.get_items_by_parent(parent_item)

        # XXX
        if content == [] or content is None:
            content = await self._read_dir_content(parent_item)

        content = content[off:]

        for idx, sub_item in enumerate(content, off):
            resp = pyfuse3.readdir_reply(
                token,
                str.encode(sub_item.data.structure_item.name),
                sub_item.data.attrs,
                idx + 1,
            )

            if resp is False:
                break

    @exception_handler
    async def _old_readdir(self, fh, off, token: pyfuse3.ReaddirToken):
        logger.debug(f"= readdir(fh={fh}, off={off})")

        parent_item, handle = self._handlers.get_by_fh(fh)

        if parent_item is None:
            logger.error("= readdir(fh={fh}, off={off}): missing parent_item")
            raise pyfuse3.FUSEError()

        if not DirLike.guard(parent_item.data.structure_item):
            logger.error("= readdir(fh={fh}, off={off}): parent_item is not folder")
            raise pyfuse3.FUSEError()

        # if parent_item.data.structure_item.content is None:
        #     logger.debug("= readdir(): parent_item has no content")
        #     return

        rels: list[DirContentItem] = [
            # self._inodes.get_item_by_name(fsencode('.'), parent_item.inode),
            # self._inodes.get_item_by_name(fsencode('..'), parent_item.inode)
        ]

        for idx, sub_item in enumerate(
            [
                *rels,
                *await parent_item.data.structure_item.content.readdir_func(
                    handle, off
                ),
            ],
            off,
        ):

            logger.debug(f"= readdir(fh={fh}, off={off}): subitem {sub_item.name}")

            fs_item = self._inodes.get_child_item_by_name(
                str.encode(sub_item.name), parent_item.inode
            )

            if fs_item is None:
                fs_item = self._inodes.add_item_to_inodes(
                    str.encode(sub_item.name),
                    self.create_FileSystemItem(
                        sub_item,
                        self._create_attributes_for_item(sub_item, inode=0),
                    ),
                    parent_inode=parent_item.inode,
                )
                fs_item.data.attrs.st_ino = fs_item.inode

            logger.debug(
                f'= readdir(): replying fs_item "%{fs_item.data.structure_item.name}" inode={fs_item.inode}',
            )

            resp = pyfuse3.readdir_reply(
                token,
                str.encode(fs_item.data.structure_item.name),
                fs_item.data.attrs,
                idx + 1,
            )

            if resp is False:
                break

    @exception_handler
    async def releasedir(self, fh):
        logger.debug(f"= releasedir({fh})")
        item, handle = self._handlers.get_by_fh(fh)

        if item is None:
            logger.debug(f"releasedir(): missing {fh} in open handles")
            return

        logger.debug(f"= releasedir({fh}) ({item.data.structure_item.name})")

        if item is None:
            logger.error(f"releasedir(): missing item with handle {fh}")
            raise pyfuse3.FUSEError(errno.ENOENT)

        if not DirLike.guard(item.data.structure_item):
            logger.error(f"releasedir(): item is not a folder {item}")
            raise pyfuse3.FUSEError()

        await item.data.structure_item.content.releasedir_func(handle)

        self._handlers.release_fh(fh)
        logger.debug("= releasedir(): ok")

    @exception_handler
    async def open(self, inode, flags, ctx):

        handle = None

        if flags & os.O_RDWR or flags & os.O_WRONLY:
            logger.error("readonly")
            raise pyfuse3.FUSEError(errno.EPERM)

        item = self._inodes.get_item_by_inode(inode)

        if item is None:
            logger.error(f"open({inode}) missing inode")
            raise pyfuse3.FUSEError(errno.ENOENT)

        logger.info(f"= open({inode}) = {item.data.structure_item.name}")

        if not FileLike.guard(item.data.structure_item):
            logger.error(f"open({inode}): is not file")
            raise pyfuse3.FUSEError(errno.EIO)

        # if item.data.structure_item.content is None:
        #     logger.debug(f"open({inode}): file has no content")

        # if (
        #     item.data.structure_item.content
        #     and item.data.structure_item.content.open_func
        # ):
        handle = await item.data.structure_item.content.open_func()

        fh = self._handlers.open_fh(item, handle)

        logger.info(
            f"- done open({inode}): fh={fh}, name={item.data.structure_item.name}"
        )

        return pyfuse3.FileInfo(fh=fh)

    @exception_handler
    async def read(self, fh, off, size):
        logger.debug(f"= read(fh={fh},off={off},size={size}).")

        item, handle = self._handlers.get_by_fh(fh)

        if item is None:
            logger.error(f"read(fh={fh}): missing item in open handles")
            raise pyfuse3.FUSEError(errno.ENOENT)

        if not FileLike.guard(item.data.structure_item):
            logger.error(f"open(fh={fh}): is not file")
            raise pyfuse3.FUSEError(errno.EIO)

        if item.data.structure_item.content is None:
            logger.debug("open(): file has no content")
            return

        chunk = await item.data.structure_item.content.read_func(handle, off, size)
        logger.debug(
            f"- read(fh={fh},off={off},size={size}) returns { len(chunk)} bytes"
        )
        return chunk

    @exception_handler
    async def release(self, fh):
        logger.info(f"= release({fh})")
        item, data = self._handlers.get_by_fh(fh)

        if item is None:
            logger.error(f"release(fh={fh}): missing item in open handles")
            return

        if not FileLike.guard(
            item.data.structure_item,
        ):
            logger.error(f"release({fh}): is not file")
            raise pyfuse3.FUSEError(errno.EIO)

        # if item.data.structure_item.content is None:
        # logger.debug("release(): file has no content")
        # self._handlers.release_fh(fh)
        # return

        # if item.data.structure_item.content.close_func:
        await item.data.structure_item.content.close_func(data)

        self._handlers.release_fh(fh)

    # async def forget(self, inode_list):
    #     pass
