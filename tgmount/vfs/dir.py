from typing import (
    Iterable,
    List,
    Union,
)

from .types.dir import (
    DirContent,
    DirContentItem,
    DirContentList,
    DirContentProto,
    DirLike,
)


def dir_content(*items: DirContentItem) -> DirContent:
    """Takes items as arguments and returns `DirContent`"""

    async def f(handle, off):
        return items[off:]

    return DirContent(readdir_func=f)


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
