from .operations import FileSystemOperations
from .update import FileSystemOperationsUpdatable, FileSystemOperationsUpdate

from .util import exception_handler
from .logger import logger


# @dataclass
# class FileSystemItem:
#     inode: int
#     structure_item: DirContentItem
#     attrs: pyfuse3.EntryAttributes
#     parent_inode: Optional[int] = None
