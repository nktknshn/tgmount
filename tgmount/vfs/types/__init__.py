from typing import Mapping, TypeVar, Union

from tgmount.vfs.types.dir import DirLike
from tgmount.vfs.types.file import FileLike, FileContentBasic

T = TypeVar("T")

Tree = Mapping[str, Union["Tree[T]", T]]

FileLikeTree = Tree[FileLike]
