import zipfile
from .zip_file import FileContentZip, ZipFileAsyncThunk


class FileContentZipFixingId3v1(FileContentZip):
    def __init__(self, z_factory: ZipFileAsyncThunk, zinfo: zipfile.ZipInfo):
        super().__init__(z_factory, zinfo)
