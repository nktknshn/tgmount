import os
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Iterable, List, Optional, Union, overload

from tgmount.vfs.file import file_content_from_file, text_content, vfile
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

FsSourceTree = DirTree[
    Union[
        str,
        list[tuple[str, FileContent]],
        FileContentProto,
        DirContentProto,
    ]
]


@overload
def root(*content: DirContentItem) -> DirLike:
    ...
    # return root(DirContentList(list(content)))


@overload
def root(content: DirContentProto) -> DirLike:
    ...
    # return DirLike(name=root_name, content=content)


@overload
def root(content: FsSourceTree) -> DirLike:
    ...
    # return DirLike(name=root_name, content=content)


def root(*content) -> DirLike:  # type: ignore
    # if isinstance(content, tuple):
    if len(content) == 1:
        if DirLike.guard(content[0]) or FileLike.guard(content[0]):
            return DirLike(name=root_name, content=DirContentList(list(content)))
        elif isinstance(content[0], dict):
            return DirLike(
                name=root_name, content=create_dir_content_from_tree(content[0])
            )
        return DirLike(name=root_name, content=content[0])

    return DirLike(name=root_name, content=DirContentList(list(content)))


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
    async def f(off):
        return items[off:]

    return DirContent(readdir_func=f)


def vdir(
    fname: str, content: Union[List[DirContentItem], DirContentProto], *, plugins=None
) -> DirLike:
    if isinstance(content, list):
        return DirLike(fname, DirContentList(content))
    else:
        return DirLike(fname, content)


def create_dir_content_from_tree(tree: FsSourceTree) -> DirContent:
    content: list[DirContentItem] = []

    for k, v in tree.items():
        if isinstance(v, dict):
            content.append(vdir(k, create_dir_content_from_tree(v)))
        elif isinstance(v, str):
            content.append(vfile(k, text_content(v)))
        elif isinstance(v, list):
            content.append(vdir(k, create_dir_content_from_tree(dict(v))))
        elif DirContentProto.guard(v):
            content.append(vdir(k, v))
        elif FileContentProto.guard(v):
            content.append(vfile(k, v))

    return dir_content(*content)
