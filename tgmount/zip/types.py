import zipfile
from typing import Callable, Awaitable

# returns handle for the underlying file content and ZipFile
ZipFileAsyncThunk = Callable[[], Awaitable[zipfile.ZipFile]]
