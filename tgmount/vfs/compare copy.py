from dataclasses import dataclass

from .dir import *
from .dir_util import *

from .compare import *


async def compare_vfs_roots_paths(
    root1: DirLike,
    root2: DirLike,
    paths: list[list[str]] = [],
):
    for path in paths:
        pass
