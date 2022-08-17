import functools
import os
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

from .file import file_content_from_file, text_content, vfile
from .types import Tree, FileLikeTree
from .types.dir import (
    DirContent,
    DirContentItem,
    DirContentList,
    DirContentProto,
    DirLike,
)
from .types.file import FileContent, FileContentProto, FileLike
from .util import lazy_list_from_thunk


def dir_content_from_fs(src_path: str) -> DirContent:
    """Use real fily system to create `DirContent`"""

    def get_content():
        content = []
        for file_name in os.listdir(src_path):
            full_path = os.path.join(src_path, file_name)

            if os.path.isdir(full_path):
                content.append(DirLike(file_name, dir_content_from_fs(full_path)))
            elif os.path.isfile(full_path):
                content.append(FileLike(file_name, file_content_from_file(full_path)))

        return content

    return DirContent(readdir_func=lazy_list_from_thunk(get_content))


def map_dir_content_items(
    mapper: Callable[[DirContentItem], DirContentItem],
    dir_content: DirContentProto,
) -> DirContent:
    async def f(handle, off):
        return map(mapper, await dir_content.readdir_func(handle, off))

    return DirContent(
        opendir_func=dir_content.opendir_func,
        releasedir_func=dir_content.releasedir_func,
        readdir_func=f,
    )


def filter_dir_content_items(
    filter: Callable[[DirContentItem], Awaitable[bool]],
    dir_content: DirContentProto,
) -> DirContent:
    async def f(handle, off):
        items = await dir_content.readdir_func(handle, off)
        res = []
        for item in items:
            if await filter(item):
                res.append(item)

        return res

    return DirContent(
        opendir_func=dir_content.opendir_func,
        releasedir_func=dir_content.releasedir_func,
        readdir_func=f,
    )


map_dir_content_f = lambda mapper: functools.partial(map_dir_content_items, mapper)


async def tree_from_dir_content(d: DirContentProto) -> FileLikeTree:
    """recursively consume `DirContentProto` returning `FileLikeTree`"""
    res: FileLikeTree = {}

    items = await read_dir_content(d)

    for item in items:
        if isinstance(item, DirLike):
            res[item.name] = await tree_from_dir_content(item.content)

        else:
            res[item.name] = item

    return res


async def map_file_like_tree(
    mapper: Callable[[FileLike], Awaitable[Any]], tree: FileLikeTree
):
    """map `FileLike` in FileLikeTree. Eg `file_like_tree_map({}, read_content_utf8)`"""
    res = {}

    for k, v in tree.items():
        if isinstance(v, FileLike):
            res[k] = await mapper(v)
        else:
            res[k] = await map_file_like_tree(mapper, v)

    return res


async def read_dir_content(content: DirContentProto) -> Iterable[DirContentItem]:
    """consume and return items from `content`. will open and release the `DirContentProto`"""
    h = await content.opendir_func()
    items = await content.readdir_func(h, 0)
    await content.releasedir_func(h)

    return items
