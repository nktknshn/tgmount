from typing import Iterable, Mapping, Sequence
from tgmount import vfs
from tgmount.zip.zip_dir_factory import DirContentZipFactory

from .zip_dir import DirContentZip


class ZipsAsDirsFactory:
    def __init__(
        self,
        dir_content_zip_factory=DirContentZipFactory,
        hide_sources=True,
        skip_folder_if_single_subfolder=False,
        zip_file_like_to_dir_name=lambda item: f"{item.name}_unzipped",
    ) -> None:
        self._dir_content_zip_factory = dir_content_zip_factory

        self._hide_sources = hide_sources
        self._skip_folder_if_single_subfolder = skip_folder_if_single_subfolder
        self._zip_file_like_to_dir_name = zip_file_like_to_dir_name

    async def wrap(self, dir_content: vfs.DirContentProto) -> vfs.DirContentProto:
        """treat zip archives as folders"""

        return vfs.DirContent(
            readdir_func=self.readdir_func(dir_content),
            opendir_func=self.opendir_func(dir_content),
            releasedir_func=self.readdir_func(dir_content),
        )

    async def _readdir_func(self, dir_content: vfs.DirContentProto, handle, off: int):
        pass

    async def readdir_func(self, dir_content: vfs.DirContentProto):
        async def readdir_func(handle, off: int):
            return await self._readdir_func(dir_content, handle, off)

        return readdir_func

    async def opendir_func(self, dir_content: vfs.DirContentProto):
        async def opendir_func():
            return await dir_content.opendir_func()

        return opendir_func

    async def releasedir_func(self, dir_content: vfs.DirContentProto):
        async def releasedir_func(handle):
            return await dir_content.releasedir_func(handle)

        return releasedir_func
