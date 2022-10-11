import logging
import logging
import os
import zipfile
from typing import (
    Any,
    Awaitable,
    Callable,
    List,
)

import greenback

from tgmount import vfs
from tgmount.vfs.io import FileContentIOGreenlet
from .types import ZipFileAsyncThunk
from .util import ZipTree, get_zip_tree, get_zipinfo_list, ls_zip_tree
from .zip_file import FileContentZip
from .zip_file_id3v1_fix import FileContentZipFixingId3v1

from tgmount.util import none_fallback

logger = logging.getLogger("tgmount-zip")

FileContentFactory = Callable[
    [
        ZipFileAsyncThunk,
        zipfile.ZipInfo,
    ],
    Awaitable[vfs.FileContentProto],
]

ZipFileHandle = Any
ZipFileFactory = Callable[[vfs.FileContentProto], Awaitable[zipfile.ZipFile]]
ZipDirContentFactory = Callable[
    [list[vfs.DirContentItem]], Awaitable[vfs.DirContentProto]
]


async def zipfile_factory(
    file_content: vfs.FileContentProto,
) -> zipfile.ZipFile:
    """async thunk so tasks can spawn their own handles for reading files inside a zip"""

    await greenback.ensure_portal()  # type: ignore

    file_handle = await file_content.open_func()

    # XXX close
    # async IO interface usable in non async code

    fc = FileContentIOGreenlet(file_content, file_handle)

    try:
        zf = zipfile.ZipFile(fc)
    except zipfile.BadZipFile as e:
        logger.error(f"zipfile.BadZipFile: {file_content}")
        raise
    else:
        return zf


async def file_content_factory(
    get_zipfile: ZipFileAsyncThunk,
    zinfo: zipfile.ZipInfo,
):

    if zinfo.filename.endswith(".mp3") or zinfo.filename.endswith(".flac"):
        return FileContentZipFixingId3v1(get_zipfile, zinfo)

    return FileContentZip(get_zipfile, zinfo)


class DirContentZipFactory:
    """takes zip file's `FileContentProto` and produces `DirContentProto`"""

    def __init__(
        self,
        zipfile_factory=zipfile_factory,
        file_content_factory=file_content_factory,
        dir_content_factory=vfs.DirContentList,
    ) -> None:
        self._file_content_factory: FileContentFactory = file_content_factory
        self._zipfile_factory: ZipFileFactory = zipfile_factory
        self._dir_content_factory = dir_content_factory

    def _get_thunk(self, file_content: vfs.FileContentProto) -> ZipFileAsyncThunk:
        async def _inner() -> zipfile.ZipFile:
            return await self._zipfile_factory(file_content)

        return _inner

    async def create_dir_content_from_ziptree(
        self,
        file_content: vfs.FileContentProto,
        zt: ZipTree,
    ) -> vfs.DirContentList:

        subfiles = [v for v in zt.values() if isinstance(v, zipfile.ZipInfo)]

        subdirs: list[tuple[str, ZipTree]] = [
            (k, v) for k, v in zt.items() if isinstance(v, dict)
        ]

        subfilelikes = [
            await self._create_filelike(file_content, zinfo) for zinfo in subfiles
        ]

        subdirlikes = [
            await self._create_dirlike(file_content, dir_name, dir_zt)
            for dir_name, dir_zt in subdirs
        ]

        return self._dir_content_factory([*subfilelikes, *subdirlikes])

    async def get_ziptree(
        self,
        file_content: vfs.FileContentProto,
        path=[],
    ):
        zf = await self._zipfile_factory(file_content)
        zt = get_zip_tree(get_zipinfo_list(zf))
        zt = ls_zip_tree(zt, none_fallback(path, []))

        if zt is None:
            raise ValueError(f"invalid path: {path}")

        return zt

    # async def create_dir_content(
    #     self,
    #     file_content: vfs.FileContentProto,
    #     path: List[str] = [],
    # ) -> vfs.DirContentProto:

    #     zt = await self.get_ziptree(file_content, path)

    #     return await self.create_dir_content_from_ziptree(file_content, zt)

    async def _create_filelike(
        self, file_content: vfs.FileContentProto, zinfo: zipfile.ZipInfo
    ) -> vfs.FileLike:
        return vfs.FileLike(
            os.path.basename(zinfo.filename),
            await self._file_content_factory(self._get_thunk(file_content), zinfo),
        )

    async def _create_dirlike(
        self,
        file_content: vfs.FileContentProto,
        dir_name: str,
        dir_zt: ZipTree,
    ):
        return vfs.DirLike(
            dir_name,
            await self.create_dir_content_from_ziptree(file_content, dir_zt),
        )
