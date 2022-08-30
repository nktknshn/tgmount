from typing import (
    Iterable,
)

from .types.dir import (
    DirContent,
    DirContentItem,
    DirContentList,
    DirContentProto,
    DirLike,
)


def dir_content(*items: DirContentItem) -> DirContent[None]:
    """Takes items as arguments and returns `DirContent`"""

    async def readdir_func(handle: None, off):
        return items[off:]

    return DirContent(readdir_func=readdir_func)


def vdir(
    fname: str, content: DirContentProto | Iterable[DirContentItem], extra=None
) -> DirLike:
    """Constructor for `DirLike`. `content` is either `DirContentProto`
    or Iterable of `DirContentItem`"""
    if isinstance(content, (list, Iterable)):
        return DirLike(fname, DirContentList(list(content)), extra=extra)
    else:
        return DirLike(fname, content, extra=extra)
