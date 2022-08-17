from typing import (
    Iterable,
    Mapping,
    TypeGuard,
    Union,
)

from .dir import vdir, dir_content
from .file import vfile
from .types import Tree
from .types.dir import (
    DirContent,
    DirContentItem,
    DirContentProto,
    DirLike,
)
from .types.file import FileContentProto, FileLike

FsSourceTreeValue = Union[
    # dir
    DirContentProto,
    Iterable[FileLike],
    Iterable[DirLike],
    Iterable[DirLike | FileLike],
    # file
    FileContentProto,
]

"""
`DirContentSourceTree` represents structure that can be used as a source for building a DirContent
"""
DirContentSourceTree = Tree[FsSourceTreeValue]


def is_tree(v) -> TypeGuard[DirContentSourceTree]:
    return isinstance(v, Mapping)


def dir_content_from_tree(tree: DirContentSourceTree) -> DirContent:
    content: list[DirContentItem] = []

    for k, v in tree.items():
        # DirTree case

        if is_tree(v):
            content.append(vdir(k, dir_content_from_tree(v)))
        elif isinstance(v, (list, Iterable)):
            content.append(vdir(k, list(v)))
        elif DirContentProto.guard(v):
            content.append(vdir(k, v))
        elif FileContentProto.guard(v):
            content.append(vfile(k, v))

    return dir_content(*content)
