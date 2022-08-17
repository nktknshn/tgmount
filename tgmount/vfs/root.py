from typing import overload
from .dir import DirLike, DirContentList, DirContentItem, DirContentProto
from .tree import DirContentSourceTree, dir_content_from_tree
from .file import FileLike

VfsRoot = DirLike

root_name = "<root>"


@overload
def root(*content: DirContentItem) -> VfsRoot:
    ...
    # return root(DirContentList(list(content)))


@overload
def root(content: DirContentProto) -> VfsRoot:
    ...
    # return DirLike(name=root_name, content=content)


@overload
def root(content: DirContentSourceTree) -> VfsRoot:
    ...
    # return DirLike(name=root_name, content=content)


def root(*content) -> VfsRoot:  # type: ignore
    # if isinstance(content, tuple):
    if len(content) == 1:
        if DirLike.guard(content[0]) or FileLike.guard(content[0]):
            return VfsRoot(root_name, DirContentList(list(content)))
        elif isinstance(content[0], dict):
            return VfsRoot(root_name, dir_content_from_tree(content[0]))
        return VfsRoot(root_name, content[0])

    return VfsRoot(root_name, DirContentList(list(content)))
