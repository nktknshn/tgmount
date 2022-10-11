import os
from typing import Optional
from zipfile import ZipFile, ZipInfo

from tgmount import util
from tgmount.util.func import (
    fst,
    group_by,
    list_filter,
)
from tgmount.vfs import Tree
from tgmount.vfs.util import norm_and_parse_path

ZipTree = Tree[ZipInfo]


def is_file(zi: ZipInfo):
    return not zi.filename.endswith("/")


def get_zipinfo_list(zf: ZipFile, *, filter_non_relative=True) -> list[ZipInfo]:
    """
    Returns a list of `ZipInfo`
    excluding dirs themselves
    excluding global paths (ones starting with `/`) if needed
    """
    filelist = list_filter(is_file, zf.infolist())

    if filter_non_relative:
        filelist = list_filter(lambda f: not f.filename.startswith("/"), filelist)

    return filelist


def get_zip_tree(filelist: list[ZipInfo]) -> ZipTree:
    """ZipTree is a recursive `Mapping` where values are eventually `ZipInfo`"""
    dirs = [norm_and_parse_path(f.filename) for f in filelist]
    dirs = [[*ds[:-1], zi] for zi, ds in zip(filelist, dirs)]

    return group_dirs_into_tree(dirs)


def zip_ls(zf: ZipFile, path: list[str] = []) -> (ZipTree | None):
    """
    ignores global paths (paths starting with `/`).
    to get zip's root listing use `path = []` which is default
    """

    filelist = get_zipinfo_list(zf)
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
    """Takes `ZipTree` and `path` (list of dir names) and returns `ZipTree` at the `path`"""
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


def get_uniq_name(names: list[str], name: str):
    same = util.find(lambda a: a == name, names)

    if same is None:
        return name

    idx = 2

    while True:
        new_name = f"{name}_{idx}"
        same = util.find(lambda a: a == new_name, names)

        if same is None:
            return new_name

        idx += 1
