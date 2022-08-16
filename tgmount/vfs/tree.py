from typing import (
    Any,
    Awaitable,
    Callable,
    Coroutine,
    Iterable,
    List,
    Mapping,
    Optional,
    TypeGuard,
    TypeVar,
    Union,
    overload,
)

from .dir import vdir, dir_content
from .file import text_content, vfile
from .types import DirTree, FileLikeTree
from .types.dir import (
    DirContent,
    DirContentItem,
    DirContentList,
    DirContentProto,
    DirLike,
)
from .types.file import FileContent, FileContentProto, FileLike

FsSourceTreeValue = Union[
    # dir
    DirContentProto,
    Iterable[FileLike],
    Iterable[DirLike],
    Iterable[DirLike | FileLike],
    # file
    # str,
    FileContentProto,
]

FsSourceTree = DirTree[FsSourceTreeValue]


def is_tree(v) -> TypeGuard[FsSourceTree]:
    return isinstance(v, Mapping)


def create_dir_content_from_tree(tree: FsSourceTree) -> DirContent:
    content: list[DirContentItem] = []

    for k, v in tree.items():
        # DirTree case

        if is_tree(v):
            content.append(vdir(k, create_dir_content_from_tree(v)))
        # text content
        elif isinstance(v, str):
            content.append(vfile(k, text_content(v)))
        elif isinstance(v, (list, Iterable)):
            content.append(vdir(k, list(v)))
        elif DirContentProto.guard(v):
            content.append(vdir(k, v))
        elif FileContentProto.guard(v):
            content.append(vfile(k, v))

    return dir_content(*content)
