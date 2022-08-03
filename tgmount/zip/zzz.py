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
from tgmount.vfs.util import norm_and_parse_path
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

ZipTree = DirTree[ZipInfo]


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


def get_zip_tree(filelist: list[ZipInfo]) -> ZipTree:
    dirs = [norm_and_parse_path(f.filename) for f in filelist]
    dirs = [[*ds[:-1], zi] for zi, ds in zip(filelist, dirs)]

    return group_dirs_into_tree(dirs)


def zip_list_dir(zf: ZipFile, path: list[str] = []) -> (ZipTree | None):
    """
    ignores global paths (paths starting with `/`).
    to get zip's root listing use `path = '/'` which is default
    """

    filelist = get_filelist(zf)
    zt = get_zip_tree(filelist)

    return ls_zip_tree(zt, path)


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


def ls_zip_tree(zt: ZipTree, path: list[str] = []) -> Optional[ZipTree]:
    if path == ["/"] or path == []:
        return zt

    item_name = path[0]

    item = zt.get(item_name)

    if item is None:
        return

    if isinstance(item, ZipInfo):
        # if len(path) > 1:
        return

        # return item

    return ls_zip_tree(item, path[1:])
