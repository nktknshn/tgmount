import os
from typing import Any, Awaitable, ByteString, Callable, Optional, TypeVar, Union
from zipfile import Path as ZipPath
from zipfile import ZipFile, ZipInfo
from tgmount.vfs import DirTree
from tgmount.vfs.file import FileLike
from tgmount.vfs.dir import DirContentProto
from tgmount.vfs.types import FileLikeTree
from tgmount.vfs.types.dir import DirLike
from tgmount.vfs.types.file import FileContentProto
from tgmount.zip.util import (
    cmap,
    compose,
    fst,
    group_by,
    list_filter,
    list_map,
    set_map,
    walk_values,
)
from tgmount.vfs.lookup import get_dir_content_items, list_dir_by_path, napp


def is_file(zi: ZipInfo):
    return not zi.filename.endswith("/")


def get_filelist(zf: ZipFile, *, filter_non_relative=True) -> list[ZipInfo]:
    """
    removes dirs
    removes global pathes if needed

    """
    filelist = list_filter(is_file, zf.infolist())

    if filter_non_relative:
        filelist = list_filter(lambda f: not f.filename.startswith("/"), filelist)

    return filelist


def group_dirs_into_tree(dirs: list[list]):
    """
    input:
    [
        ['a', ZipInfo('a/file1.txt`)],
        ['a', ZipInfo('a/file2.txt`)],
        ['a', 'b', ZipInfo('a/b/file3.txt`)],
        ['a', 'b', 'c', ZipInfo('a/b/c/file4.txt`)],
    ]

    output:
    {
        a: {
            'file1.txt`: ZipInfo('a/file1.txt`),
            'file2.txt`: ZipInfo('a/file2.txt`),
            b: {
                'file3.txt`: ZipInfo('a/b/file3.txt`),
                c: {
                    'file4.txt`: ZipInfo('a/b/c/file4.txt`)
                }
            }
        }
    }
    """
    res = {}

    for k, v in group_by(fst, dirs).items():
        if isinstance(k, str):
            # this is directory
            res[k] = group_dirs_into_tree([v[1:] for v in v])
        else:
            # this is a file
            res[os.path.basename(k.filename)] = k

    return res


ZipTree = DirTree[ZipInfo]


async def read_file_content_bytes(fc: FileContentProto) -> bytes:
    handle = await fc.open_func()
    data = await fc.read_func(handle, 0, fc.size)
    await fc.close_func(handle)

    return data


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
