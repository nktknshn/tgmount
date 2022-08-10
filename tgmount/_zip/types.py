import zipfile
from typing import Any, Callable, Awaitable, Tuple
import dataclasses
from ..vfs.types.file import FileContentHandle
    
# returns handle for the underlying file content and ZipFile
ZipFileAsyncThunk = Callable[[], Awaitable[Tuple[FileContentHandle, zipfile.ZipFile]]]
