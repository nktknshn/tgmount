from dataclasses import dataclass
from typing import Optional

import pyfuse3
from tgmount.vfs import DirContentItem

from .operations2 import FileSystemOperations
from .update import FileSystemOperationsUpdatable


# @dataclass
# class FileSystemItem:
#     inode: int
#     structure_item: DirContentItem
#     attrs: pyfuse3.EntryAttributes
#     parent_inode: Optional[int] = None
