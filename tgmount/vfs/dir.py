import os
from dataclasses import dataclass
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
from typing_extensions import reveal_type

from tgmount.vfs.file import file_content_from_file, text_content, vfile
from tgmount.vfs.types import FileLikeTree
from tgmount.vfs.types.dir import (
    DirContent,
    DirContentProto,
    DirLike,
    DirContentList,
    DirContentItem,
)
from tgmount.vfs.types.file import FileContent, FileContentProto, FileLike
from tgmount.vfs.util import lazy_list_from_thunk
from tgmount.vfs import DirTree

root_name = "<root>"


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

VfsRoot = DirLike


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


@overload
def root(*content: DirContentItem) -> VfsRoot:
    ...
    # return root(DirContentList(list(content)))


@overload
def root(content: DirContentProto) -> VfsRoot:
    ...
    # return DirLike(name=root_name, content=content)


@overload
def root(content: FsSourceTree) -> VfsRoot:
    ...
    # return DirLike(name=root_name, content=content)


def root(*content) -> VfsRoot:  # type: ignore
    # if isinstance(content, tuple):
    if len(content) == 1:
        if DirLike.guard(content[0]) or FileLike.guard(content[0]):
            return VfsRoot(root_name, DirContentList(list(content)))
        elif isinstance(content[0], dict):
            return VfsRoot(root_name, create_dir_content_from_tree(content[0]))
        return VfsRoot(root_name, content[0])

    return VfsRoot(root_name, DirContentList(list(content)))


def dir_content_from_dir(src_path: str) -> DirContent:
    def get_content():
        content = []
        for file_name in os.listdir(src_path):
            full_path = os.path.join(src_path, file_name)

            if os.path.isdir(full_path):
                content.append(DirLike(file_name, dir_content_from_dir(full_path)))
            elif os.path.isfile(full_path):
                content.append(FileLike(file_name, file_content_from_file(full_path)))

        return content

    return DirContent(readdir_func=lazy_list_from_thunk(get_content))


def dir_content(*items: DirContentItem) -> DirContent:
    async def f(handle, off):
        return items[off:]

    return DirContent(readdir_func=f)


def map_dir_content(
    mapper: Callable[[DirContentItem], DirContentItem], dir_content: DirContentProto
) -> DirContent:
    async def f(handle, off):
        return map(mapper, await dir_content.readdir_func(handle, off))

    return DirContent(
        opendir_func=dir_content.opendir_func,
        releasedir_func=dir_content.releasedir_func,
        readdir_func=f,
    )


import functools

map_dir_content_f = lambda mapper: functools.partial(map_dir_content, mapper)


def vdir(
    fname: str,
    content: Union[List[DirContentItem], DirContentProto | Iterable],
    *,
    plugins=None
) -> DirLike:
    if isinstance(content, (list, Iterable)):
        return DirLike(fname, DirContentList(list(content)))
    else:
        return DirLike(fname, content)


async def get_dir_content_items(content: DirContentProto) -> Iterable[DirContentItem]:
    handle = await content.opendir_func()
    items = await content.readdir_func(handle, 0)
    await content.releasedir_func(handle)

    return items


async def dir_content_get_tree(d: DirContentProto) -> FileLikeTree:
    res: FileLikeTree = {}

    items = await get_dir_content_items(d)

    for item in items:
        if isinstance(item, DirLike):
            res[item.name] = await dir_content_get_tree(item.content)

        else:
            res[item.name] = item

    return res


async def file_like_tree_map(
    tree: FileLikeTree, f: Callable[[FileLike], Awaitable[Any]]
):
    res = {}

    for k, v in tree.items():
        if isinstance(v, FileLike):
            res[k] = await f(v)
        else:
            res[k] = await file_like_tree_map(v, f)

    return res
    # return walk_values(
    #     lambda v: f(v) if isinstance(v, FileLike) else tree_map(v, f), tree
    # )
