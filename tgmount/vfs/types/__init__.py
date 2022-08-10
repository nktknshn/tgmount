from typing import Mapping, TypeVar, Union

from tgmount.vfs.types.dir import DirLike
from tgmount.vfs.types.file import FileLike


T = TypeVar("T")

DirTree = Mapping[str, Union["DirTree[T]", T]]

FileLikeTree = DirTree[FileLike]
