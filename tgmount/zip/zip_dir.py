import logging
import logging
import os
import zipfile
from typing import Iterable, List, Optional

import greenback

from tgmount import vfs
from tgmount.vfs.dir import DirContentProto, DirLike
from tgmount.vfs.file import FileLike
from tgmount.vfs.io import FileContentIOGreenlet
from tgmount.vfs.types.dir import DirContentItem
from tgmount.vfs.types.file import FileContentProto
from .util import (
    ZipTree,
    get_zipinfo_list,
    get_zip_tree,
    ls_zip_tree,
)
from .zip_file import FileContentZip

logger = logging.getLogger("tgmount-zip")


class DirContentZip(DirContentProto[vfs.DirContentList]):
    """
    creates DirContent from FileContentProto which provides zip file content
    """

    # zf: zipfile.ZipFile
    @staticmethod
    def create_dir_content_zip(
        zip_file_content: FileContentProto,
        path: List[str] = [],
    ) -> "DirContentZip":
        return DirContentZip(
            zip_file_content,
            path=path,
            # recursive=False,
        )

    def __init__(
        self,
        file_content: FileContentProto,
        *,
        path: List[str] = [],
        # recursive=False,
    ):

        self._file_content = file_content
        self._path = path

    async def get_single_root_dir(self) -> Optional[str]:
        """Returns root dir name if there is a single root dir containing all the other file
        otherwise returns None
        """
        zt = await self.get_zip_tree()

        root_items = list(zt.items())

        root_dir_name, root_dir = root_items[0]

        is_single_root_dir = len(root_items) == 1 and isinstance(root_dir, dict)

        if is_single_root_dir:
            return root_dir_name

        return None

    async def get_zipfile(self) -> zipfile.ZipFile:
        """async thunk so tasks can spawn their own handles for reading files inside a zip"""

        await greenback.ensure_portal()  # type: ignore

        file_handle = await self._file_content.open_func()

        # XXX close
        # async IO interface usable in non async code

        fh = file_handle
        fc = FileContentIOGreenlet(self._file_content, file_handle)
        zf = zipfile.ZipFile(fc)

        return zf

    async def get_zip_tree(self, path=None):
        """Returns"""
        zf = await self.get_zipfile()

        filelist = get_zipinfo_list(zf)
        zt = ls_zip_tree(
            get_zip_tree(filelist),
            path if path is not None else self._path,
        )

        if zt is None:
            raise ValueError(f"invalid path: {self._path}")

        return zt

    def create_file_content_from_zipinfo(self, zinfo: zipfile.ZipInfo):
        return FileContentZip(self.get_zipfile, zinfo)

    def create_filelike_from_zipinfo(self, zinfo: zipfile.ZipInfo) -> FileLike:
        return FileLike(
            os.path.basename(zinfo.filename),
            self.create_file_content_from_zipinfo(zinfo),
        )

    def create_dirlike(self, dir_name: str, dir_zt: ZipTree):
        return DirLike(
            dir_name,
            self.create_dir_content_from_ziptree(dir_zt),
        )

    def create_dir_content_from_ziptree(
        self,
        zt: ZipTree,
    ) -> vfs.DirContentList:
        """
        files are files
        dirs are dirs
        """
        subfiles = [v for v in zt.values() if isinstance(v, zipfile.ZipInfo)]

        subdirs: list[tuple[str, ZipTree]] = [
            (k, v) for k, v in zt.items() if isinstance(v, dict)
        ]

        subfilelikes = [self.create_filelike_from_zipinfo(zinfo) for zinfo in subfiles]

        subdirlikes = [
            self.create_dirlike(dir_name, dir_zt) for dir_name, dir_zt in subdirs
        ]

        return vfs.DirContentList([*subfilelikes, *subdirlikes])

    # DirContentProto impl
    async def opendir_func(self) -> vfs.DirContentList:
        """Returns DirContentProto as handle"""

        logger.debug(f"DirContentFromZipFileContent.opendir_func()")

        return self.create_dir_content_from_ziptree(
            await self.get_zip_tree(),
        )

    async def readdir_func(
        self, handle: DirContentProto, off: int
    ) -> Iterable[DirContentItem]:
        logger.debug(f"ZipDirContent.readdir_func()")
        return await handle.readdir_func(None, off)

    async def releasedir_func(self, handle: DirContentProto):
        await handle.releasedir_func(None)
