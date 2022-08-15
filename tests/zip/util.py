import io
import os
from typing import (
    List,
    Tuple,
)
from zipfile import ZipFile
from tgmount.vfs import FileLike, DirTree, read_file_content_bytes

ZipSourceTreeValue = str | io.BytesIO | bytes
ZipSourceTree = DirTree[ZipSourceTreeValue]


def zip_tree_to_list(
    tree: ZipSourceTree, cpath=""
) -> List[Tuple[str, ZipSourceTreeValue]]:
    res = []

    for k, v in tree.items():
        p = os.path.join(cpath, k)
        if isinstance(v, str):
            res.append((p, v))
        elif isinstance(v, io.BytesIO):
            res.append((p, v))
        elif isinstance(v, bytes):
            res.append((p, v))
        elif isinstance(v, dict):
            res = [*res, *zip_tree_to_list(v, p)]

    return res


def create_zip_from_tree(tree: ZipSourceTree):

    data = io.BytesIO()
    zf = ZipFile(data, "w")

    items = zip_tree_to_list(tree)

    for (path, item) in items:
        if isinstance(item, str):
            zf.writestr(path, item)
        elif isinstance(item, io.BytesIO):
            zf.writestr(path, item.getbuffer())
        elif isinstance(item, bytes):
            zf.writestr(path, item)

    zf.close()

    return zf, data


async def get_size(v: FileLike):
    return v.content.size


async def get_file_content_str_utf8(v: FileLike) -> str:
    bs = await read_file_content_bytes(v.content)

    return bs.decode("utf-8")
