import io
import logging
import os
import zipfile
from typing import Iterable, List, Mapping, Optional, Tuple

import greenback
from tgmount.vfs.dir import DirContentList, DirContentProto, DirLike
from tgmount.vfs.file import FileLike
from tgmount.vfs.io import FileContentIOGreenlet
from tgmount.vfs.types.dir import DirContentItem
from tgmount.vfs.types.file import FileContentHandle, FileContentProto

from .types import ZipFileAsyncThunk

from .zip_file import FileContentZip
from .util import (
    ZipTree,
    get_filelist,
    get_zip_tree,
    ls_zip_tree,
)
from tgmount import vfs

"""
sadly files seeking inside a zip works by reading the offset bytes so it's slow
https://github.com/python/cpython/blob/main/Lib/zipfile.py#L1116

also id3v1 tags are stored in the end of a file :)
https://github.com/quodlibet/mutagen/blob/master/mutagen/id3/_id3v1.py#L34

and most of the players try to read it. So just adding an mp3 or flac
to a player will fetch the whole file from the archive

setting hacky_handle_mp3_id3v1 will patch reading function so it
always returns 4096 zero bytes when reading a block of 4096 bytes
(usually players read this amount looking for id3v1 (requires
investigation to find a less hacky way)) from an mp3 or flac file
inside a zip archive
"""

""" 

Ensure that the current async task is able to use greenback.await_.

If the current task has called ensure_portal previously, calling it again is a no-op. Otherwise, ensure_portal interposes a "coroutine shim" provided by greenback in between the event loop and the coroutine being used to run the task. For example, when running under Trio, trio.lowlevel.Task.coro is replaced with a wrapper around the coroutine it previously referred to. (The same thing happens under asyncio, but asyncio doesn't expose the coroutine field publicly, so some additional trickery is required in that case.)

After installation of the coroutine shim, each task step passes through greenback on its way into and out of your code. At some performance cost, this effectively provides a portal that allows later calls to greenback.await_ in the same task to access an async environment, even if the function that calls await_ is a synchronous function.

"""

logger = logging.getLogger("tgmount-zip")


def create_dir_content(
    zip_file_content: FileContentProto,
    path: List[str] = [],
) -> "DirContentZip":
    return DirContentZip(
        zip_file_content,
        path=path,
        # recursive=False,
    )


class DirContentZip(DirContentProto[vfs.DirContentList]):
    """
    creates DirContent from FileContentProto which provides zip file content
    """

    # zf: zipfile.ZipFile

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

    # async thunk so workers can spawn their own handles for reading inner files
    async def get_zipfile(self) -> Tuple[FileContentHandle, zipfile.ZipFile]:
        """reads file content"""

        await greenback.ensure_portal()  # type: ignore

        file_handle = await self._file_content.open_func()

        # XXX close
        # async IO interface usable in non async code

        fh = FileContentHandle(self._file_content, file_handle)
        fc = FileContentIOGreenlet(self._file_content, file_handle)
        zf = zipfile.ZipFile(fc)

        return fh, zf

    async def get_zip_tree(self):
        h, zf = await self.get_zipfile()

        filelist = get_filelist(zf)
        zt = get_zip_tree(filelist)
        zt = ls_zip_tree(zt, self._path)

        if zt is None:
            raise ValueError(f"invalid path: {self._path}")

        return zt

    def create_file_content_from_zipinfo(self, zinfo: zipfile.ZipInfo):
        return FileContentZip(self.get_zipfile, zinfo)

    def create_filelike_from_zipinfo(self, zinfo: zipfile.ZipInfo):
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
