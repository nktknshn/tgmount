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

DirContentSourceTreeValueDir = Union[
    # dir
    DirContentProto,
    Iterable[FileLike],
    Iterable[DirLike],
    Iterable[DirLike | FileLike],
]
DirContentSourceTreeValue = Union[
    # dir
    DirContentSourceTreeValueDir,
    # file
    FileContentProto,
]

"""
`DirContentSourceTree` represents structure that can be used as a source for building a DirContent
"""
DirContentSourceTree = Tree[DirContentSourceTreeValue]

DirContentSource = DirContentSourceTree | DirContentSourceTreeValueDir


def is_tree(v) -> TypeGuard[DirContentSourceTree]:
    return isinstance(v, Mapping)


def dir_content_from_tree(tree: DirContentSourceTree) -> DirContent:
    content: list[DirContentItem] = []

    for k, v in tree.items():
        # DirTree case

        if is_tree(v):
            content.append(vdir(k, dir_content_from_tree(v)))
        elif isinstance(v, (list, Iterable)):
            if not isinstance(v, Mapping):
                content.append(vdir(k, list(v)))
            else:
                raise ValueError(f"{v} shouldnt be Mapping here")
        elif DirContentProto.guard(v):
            content.append(vdir(k, v))
        elif FileContentProto.guard(v):
            content.append(vfile(k, v))

    return dir_content(*content)
