import io
import logging
import os
import zipfile
from dataclasses import dataclass
from functools import partial
from typing import Any, Awaitable, Callable, Iterable, List, Optional, Tuple, Union

import greenback
from tgmount.vfs.dir import DirContentList, DirContentProto, DirLike
from tgmount.vfs.file import FileLike
from tgmount.vfs.io import FileContentIOGreenlet
from tgmount.vfs.types.dir import DirContentItem
from tgmount.vfs.types.file import FileContentHandle, FileContentProto
from tgmount.vfs.util import norm_and_parse_path
from tgmount.zip.types import ZipFileAsyncThunk

from tgmount.zip.zip_file import create_filelike_from_zipinfo
from tgmount.zip.zzz import ZipTree, get_filelist, group_dirs_into_tree

""" 

Ensure that the current async task is able to use greenback.await_.

If the current task has called ensure_portal previously, calling it again is a no-op. Otherwise, ensure_portal interposes a "coroutine shim" provided by greenback in between the event loop and the coroutine being used to run the task. For example, when running under Trio, trio.lowlevel.Task.coro is replaced with a wrapper around the coroutine it previously referred to. (The same thing happens under asyncio, but asyncio doesn't expose the coroutine field publicly, so some additional trickery is required in that case.)

After installation of the coroutine shim, each task step passes through greenback on its way into and out of your code. At some performance cost, this effectively provides a portal that allows later calls to greenback.await_ in the same task to access an async environment, even if the function that calls await_ is a synchronous function.

"""

logger = logging.getLogger("tgmount-zip")


class DirContentFromZipFileContent(DirContentProto[DirContentProto]):
    """
    creates DirContent from FileContentProto which provides zip file content
    """

    # zf: zipfile.ZipFile

    def __init__(
        self,
        file_content: FileContentProto,
        path: List[str] = [],
    ):
        logger.debug("DirContentFromZipFileContent()")

        self._file_content = file_content
        self.path = path

    # async thunk so workers can spawn their own handles
    async def get_zipfile(self) -> Tuple[FileContentHandle, zipfile.ZipFile]:
        await greenback.ensure_portal()  # type: ignore

        handle = await self._file_content.open_func()

        # XXX close
        # async IO interface usable in non async code
        fp = FileContentIOGreenlet(self._file_content, handle)

        return FileContentHandle(self._file_content, handle), zipfile.ZipFile(fp)

    async def opendir_func(self) -> DirContentProto:
        """Returns DirContentProto as handle"""

        logger.debug(f"DirContentFromZipFileContent.opendir_func()")

        h, zf = await self.get_zipfile()

        filelist = get_filelist(zf)
        zt = get_zip_tree(filelist)
        zt = ls_zip_tree(zt, self.path)

        if zt is None:
            raise ValueError(f"invalid path: {self.path}")

        return create_dir_content_from_ziptree(zt, self.get_zipfile)
        # XXX await h.close()

    async def readdir_func(
        self, handle: DirContentProto, off: int
    ) -> Iterable[DirContentItem]:
        logger.debug(f"ZipDirContent.readdir_func()")
        return await handle.readdir_func(None, off)

    async def releasedir_func(self, handle: DirContentProto):
        # XXX ZipFile.close
        await handle.releasedir_func(None)


def create_dir_content_from_ziptree(
    zt: ZipTree,
    zipfile_async_thunk: ZipFileAsyncThunk,
    # path: Optional[List[str]] = None,
) -> DirContentList:
    """
    files are files
    dirs are dirs
    """
    subfiles = [v for v in zt.values() if isinstance(v, zipfile.ZipInfo)]

    subdirs: list[tuple[str, ZipTree]] = [
        (k, v) for k, v in zt.items() if isinstance(v, dict)
    ]

    subfilelikes = [
        create_filelike_from_zipinfo(zipfile_async_thunk, zinfo) for zinfo in subfiles
    ]

    subdirlikes = [
        DirLike(
            dir_name,
            ZipsAsDirs(create_dir_content_from_ziptree(dir_zt, zipfile_async_thunk)),
        )
        for dir_name, dir_zt in subdirs
    ]

    return DirContentList([*subfilelikes, *subdirlikes])


def get_zip_tree(filelist: list[zipfile.ZipInfo]) -> ZipTree:
    dirs = [norm_and_parse_path(f.filename) for f in filelist]
    dirs = [[*ds[:-1], zi] for zi, ds in zip(filelist, dirs)]

    return group_dirs_into_tree(dirs)


def ls_zip_tree(zt: ZipTree, path: list[str] = []) -> Optional[ZipTree]:
    if path == ["/"] or path == []:
        return zt

    item_name = path[0]

    item = zt.get(item_name)

    if item is None:
        return

    if isinstance(item, zipfile.ZipInfo):
        # if len(path) > 1:
        return

        # return item

    return ls_zip_tree(item, path[1:])


def zip_list_dir(zf: zipfile.ZipFile, path: list[str] = []) -> (ZipTree | None):
    """
    ignores global paths (paths starting with `/`).
    to get zip's root listing use `path = '/'` which is default
    """

    filelist = get_filelist(zf)
    zt = get_zip_tree(filelist)

    return ls_zip_tree(zt, path)


class ZipsAsDirs(DirContentProto[list[DirContentItem]]):
    """ "
    Wraps DirContentProto recursively (including nested folders) providing support for zip archives
    """

    def __init__(
        self,
        source_dir_content: DirContentProto,
        *,
        hide_sources=True,
        skip_folder_if_single_subfolder=False,
        zip_file_like_to_dir_name=lambda item: f"{item.name}_unzipped",
        # zip_dir_from_file_factory=ZipDirContentFromFile,
    ):
        self.source_dir_content = source_dir_content

        self.hide_sources = hide_sources
        self.skip_folder_if_single_subfolder = skip_folder_if_single_subfolder
        self.zip_file_like_to_dir_name = zip_file_like_to_dir_name

        # self.zip_dir_from_file_factory = zip_dir_from_file_factory

    async def _mount_zip(self, item: FileLike, content: List[DirContentItem]):
        """
        prcoesses zip archive's FileLike
        """
        zfc = DirContentFromZipFileContent(item.content)

        h, zf = await zfc.get_zipfile()

        # XXX await h.close()

        filelist = get_filelist(zf)
        zt = get_zip_tree(filelist)

        root_items = list(zt.items())

        root_dir_name, root_dir = root_items[0]

        is_single_root_dir = len(root_items) == 1 and isinstance(root_dir, dict)

        skip_folder_if_single_subfolder = (
            self.skip_folder_if_single_subfolder and is_single_root_dir
        )

        if not self.hide_sources:
            content.append(item)

        if not skip_folder_if_single_subfolder:
            content.append(
                DirLike(
                    item.name
                    if self.hide_sources
                    else self.zip_file_like_to_dir_name(item.name),
                    self._zips_as_dirs(
                        DirContentFromZipFileContent(item.content),
                    ),
                )
            )
        else:
            content.append(
                DirLike(
                    root_dir_name
                    if self.hide_sources
                    else self.zip_file_like_to_dir_name(root_dir_name),
                    self._zips_as_dirs(
                        DirContentFromZipFileContent(item.content, [root_dir_name])
                    ),
                )
            )

    def _zips_as_dirs(self, content):
        return zips_as_dirs(
            content,
            hide_sources=self.hide_sources,
            skip_folder_if_single_subfolder=self.skip_folder_if_single_subfolder,
            zip_file_like_to_dir_name=self.zip_file_like_to_dir_name,
        )

    async def opendir_func(self):
        logger.debug("ZipsAsDirs.opendir_func()")

        # handle = None
        # if self.source_content.opendir_func:
        handle = await self.source_dir_content.opendir_func()

        content: List[DirContentItem] = []

        for item in await self.source_dir_content.readdir_func(handle, 0):
            if isinstance(item, DirLike):
                content.append(DirLike(item.name, ZipsAsDirs(item.content)))

            elif item.name.endswith(".zip"):
                # if not self.hide_sources:
                await self._mount_zip(item, content)
            else:
                content.append(item)

        await self.source_dir_content.releasedir_func(handle)

        return content

    async def readdir_func(
        self, handle: List[DirContentItem], off: int
    ) -> list[DirContentItem]:
        logger.debug(f"ZipsAsDirs.readdir_func(off={off})")
        return handle[off:]

    async def releasedir_func(self, handle: list[DirContentItem]):
        pass


from tgmount import vfs

vfs.create_dir_content_from_tree


def zips_as_dirs(
    tree_or_content: vfs.FsSourceTree | vfs.DirContentProto,
    **kwargs,
):
    if isinstance(tree_or_content, dict):
        return ZipsAsDirs(
            vfs.create_dir_content_from_tree(tree_or_content),
            **kwargs,
        )

    return ZipsAsDirs(tree_or_content, **kwargs)
