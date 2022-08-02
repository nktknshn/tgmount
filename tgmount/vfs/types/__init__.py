from typing import TypeVar, Union

from tgmount.vfs.types.dir import DirLike
from tgmount.vfs.types.file import FileLike


T = TypeVar("T")

DirTree = dict[str, Union["DirTree[T]", T]]

FileLikeTree = DirTree[FileLike]
