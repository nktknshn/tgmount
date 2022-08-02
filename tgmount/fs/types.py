from dataclasses import dataclass
from typing import Optional, Union, Callable, Iterable, List, Any, Awaitable


@dataclass
class OpendirContext:
    full_path: Optional[str] = None
    vfs_path: Optional[str] = None


OpenDirFunc = Callable[[Optional[OpendirContext]], Awaitable[Any]]
