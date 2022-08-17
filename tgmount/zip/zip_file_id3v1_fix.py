import zipfile
from .zip_file import FileContentZip, ZipFileAsyncThunk, FileContentZipHandle


class FileContentZipFixingId3v1(FileContentZip):
    def __init__(
        self,
        z_factory: ZipFileAsyncThunk,
        zinfo: zipfile.ZipInfo,
    ):
        super().__init__(z_factory, zinfo)

    async def read_func(self, handle: FileContentZipHandle, off, size):

        # if self.zinfo.filename.endswith(".mp3") or self.zinfo.filename.endswith(
        #     ".flac"
        # ):
        if size == 4096:
            return b"\x00" * 4096
        else:
            return await self.read_func(handle, off, size)
