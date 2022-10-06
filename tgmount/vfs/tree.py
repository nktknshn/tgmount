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
    DirContentItem,
    DirContentProto,
    DirLike,
)
from .types.file import FileContentProto, FileLike
from .util import norm_and_parse_path

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
        if isinstance(content_source, (list,)):
            if not isinstance(content_source, Mapping):
                return dir_content(*content_source)
            else:
                raise ValueError(f"{content_source} shouldnt be Mapping here")
        elif DirContentProto.guard(content_source):
            return content_source

    raise ValueError(f"incorrect tree value: {content_source}")


def source_get_by_path(content_source: DirContentSource, path: str):
    npath = norm_and_parse_path(path, noslash=True)

    return _get_by_path(content_source, npath)


def _get_by_path(content_source: DirContentSource, path: list[str]):

    if path == []:
        return content_source

    if path == ["/"]:
        return content_source

    subitem = None
    subitem_name, *rest = path

    if is_tree(content_source):
        subitem = content_source.get(subitem_name)
    else:
        if isinstance(content_source, (list,)):
            for item in content_source:
                if item.name == subitem_name:
                    subitem = item
                    break
        elif DirContentProto.guard(content_source):
            raise ValueError(f"Cannot go into dir content: {path}")

    if len(rest) == 0:
        return subitem
    elif is_tree(subitem):
        return _get_by_path(subitem, path)
