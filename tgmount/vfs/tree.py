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


DirContentSourceMapping = Tree[DirContentSourceTreeValue]

"""
`DirContentSource` represents a structure that can be used as a source for
building a DirContentProto
"""
DirContentSource = DirContentSourceMapping | DirContentSourceTreeValueDir


def is_tree(v) -> TypeGuard[DirContentSourceMapping]:
    return isinstance(v, Mapping)


def dir_content_from_source(content_source: DirContentSource) -> DirContentProto:
    """Turns `DirContentSource` into `DirContentProto`"""
    if is_tree(content_source):
        content: list[DirContentItem] = []

        for k, v in content_source.items():
            if FileContentProto.guard(v):
                content.append(vfile(k, v))
            else:
                content.append(vdir(k, dir_content_from_source(v)))
        return dir_content(*content)
    else:
        if isinstance(content_source, (list, Iterable)):
            if not isinstance(content_source, Mapping):
                dir_content(*content_source)
            else:
                raise ValueError(f"{content_source} shouldnt be Mapping here")
        elif DirContentProto.guard(content_source):
            return content_source

    raise ValueError(f"incorrect tree value: {content_source}")
