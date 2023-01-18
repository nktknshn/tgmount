import io
from typing import (
    Iterable,
)

import pytest
from tgmount import vfs, zip as z

from tgmount.zip import zips_as_dirs, zip_ls

from ..helpers.zip import (
    ZipSourceTree,
    create_zip_from_tree,
    get_file_content_str_utf8,
    get_size,
)

from .fixtures import zip_tree1, zip_file1


def get_items_names(iter: Iterable[vfs.DirContentItem]):
    return list(map(lambda item: item.name, iter))


@pytest.mark.asyncio
async def test_zip(zip_file1):

    zf, zfdata = zip_file1

    a = zip_ls(zf)

    assert isinstance(a, dict)
    assert set(a.keys()) == {"a"}

    a = zip_ls(zf, ["a"])

    assert isinstance(a, dict)
    assert len(a.keys()) == 4
    assert set(a.keys()) == {"b", "d", "a1.txt", "a2.txt"}


@pytest.mark.asyncio
async def test_zip1(caplog, zip_file1):
    # caplog.set_level(logging.DEBUG)

    zf, zfdata = zip_file1

    fc = vfs.file_content_from_io(zfdata)

    structure = vfs.root(
        zips_as_dirs(
            vfs.dir_content(vfs.vfile("archive.zip", fc)),
            skip_folder_if_single_subfolder=False,
        )
    )

    items = await vfs.ls(structure, vfs.napp("/"))

    assert items
    assert get_items_names(items) == ["archive.zip"]
    assert isinstance(list(items)[0], vfs.DirLike)

    items = await vfs.ls(structure, vfs.napp("/archive.zip/"))

    assert items
    assert get_items_names(items) == ["a"]
    assert isinstance(list(items)[0], vfs.DirLike)


@pytest.mark.asyncio
async def test_zip2(zip_file1):

    zf, zfdata = zip_file1

    fc = vfs.file_content_from_io(zfdata)

    structure = vfs.root(
        zips_as_dirs(
            vfs.dir_content(vfs.vfile("archive.zip", fc)),
            skip_folder_if_single_subfolder=True,
        )
    )

    items = await vfs.ls(structure, vfs.napp("/"))

    assert items
    assert get_items_names(items) == ["a"]
    assert isinstance(list(items)[0], vfs.DirLike)

    items = await vfs.ls(structure, vfs.napp("/a"))

    assert items is not None
    assert len([*items]) == 4
    assert set(get_items_names(items)) == {"b", "d", "a1.txt", "a2.txt"}

    items = await vfs.ls(structure, vfs.napp("/a/d"))

    assert items is not None
    assert len([*items]) == 1
    assert set(get_items_names(items)) == {"a_d.txt"}

    items = await vfs.ls(structure, vfs.napp("/a/b"))

    assert items is not None
    assert len([*items]) == 4
    assert set(get_items_names(items)) == {
        "a3.txt",
        "tvrdý.txt",
        "русский файл.txt",
        "c",
    }

    items = await vfs.ls(structure, vfs.napp("/a/b/c"))

    assert items is not None
    assert len([*items]) == 1
    assert set(get_items_names(items)) == {
        "nested.txt",
    }


@pytest.mark.asyncio
async def test_zip3():

    source_tree: ZipSourceTree = {
        "a": {
            "a1.txt": "hello gravity",
            "a2.txt": "hello moon",
            "b": {
                "a3.txt": "hello starts",
                "tvrdý.txt": "hello tvrdý",
                "русский файл.txt": "hello русский файл",
                "c": {
                    "nested.txt": "hello time",
                },
            },
            "d": {"a_d.txt": "hello plants"},
        }
    }

    zf, zfdata = create_zip_from_tree(source_tree)

    structure = vfs.root(
        zips_as_dirs(
            vfs.dir_content(
                vfs.vfile("archive.zip", vfs.file_content_from_io(zfdata)),
            ),
            skip_folder_if_single_subfolder=True,
        )
    )

    tree = await vfs.dir_content_to_tree(structure.content)

    t = await vfs.file_like_tree_map(get_file_content_str_utf8, tree)

    assert t == source_tree


@pytest.mark.asyncio
async def test_zip4(zip_file1):
    zf, zfdata = zip_file1

    fc = vfs.file_content_from_io(zfdata)

    structure = vfs.root(
        zips_as_dirs(
            vfs.dir_content(vfs.vfile("archive.zip", fc)),
            skip_folder_if_single_subfolder=False,
        )
    )

    tree = await vfs.dir_content_to_tree(structure.content)

    t = await vfs.file_like_tree_map(get_size, tree)

    assert t == {
        "archive.zip": {
            "a": {
                "a1.txt": 13,
                "a2.txt": 10,
                "b": {
                    "a3.txt": 12,
                    "tvrdý.txt": 12,
                    "русский файл.txt": 29,
                    "c": {
                        "nested.txt": 10,
                    },
                },
                "d": {"a_d.txt": 12},
            }
        }
    }


# @pytest.mark.asyncio
# async def test_zip5(zip_tree1):

#     zf, zfdata = create_zip_from_tree(zip_tree1["a"])

#     structure = vfs.root(
#         zips_as_dirs(
#             vfs.dir_content(vfs.vfile("archive.zip", vfs.file_content_from_io(zfdata))),
#             skip_folder_if_single_subfolder=True,
#         )
#     )

#     tree = await vfs.dir_content_to_tree(structure.content)

#     t = await vfs.file_like_tree_map(get_file_content_str_utf8, tree)

#     assert t == {"archive.zip": zip_tree1["a"]}


@pytest.mark.asyncio
async def test_zip6(zip_tree1):
    """test recursive option"""
    zf, zfdata = create_zip_from_tree(zip_tree1)

    zfdata_bytes = zfdata.getbuffer()

    tree = await vfs.dir_content_to_tree(
        z.zips_as_dirs(
            {"a": {"b": {"c.zip": vfs.file_content_from_bytes(zfdata_bytes)}}},
            recursive=True,
        )
    )

    t = await vfs.file_like_tree_map(get_file_content_str_utf8, tree)

    assert t == {"a": {"b": {"c.zip": zip_tree1}}}

    tree = await vfs.dir_content_to_tree(
        z.zips_as_dirs(
            {"a": {"b": {"c.zip": vfs.file_content_from_bytes(zfdata_bytes)}}},
            recursive=False,
        )
    )

    t = await vfs.file_like_tree_map(get_file_content_str_utf8, tree)

    assert t == {"a": {"b": {"c.zip": zfdata_bytes}}}


@pytest.mark.asyncio
async def test_zip7(zip_tree1):
    """test skip_folder_if_single_subfolder when zips has two identical root folders"""
    zf, zfdata = create_zip_from_tree(zip_tree1)

    structure = vfs.root(
        z.zips_as_dirs(
            {
                "a": {
                    "b": {
                        "c.zip": vfs.file_content_from_io(zfdata),
                        "cc.zip": vfs.file_content_from_io(zfdata),
                    }
                }
            },
            recursive=True,
            skip_folder_if_single_subfolder=True,
        )
    )

    tree = await vfs.dir_content_to_tree(structure.content)

    t = await vfs.file_like_tree_map(get_file_content_str_utf8, tree)

    assert t == {
        "a": {
            "b": {
                "a": zip_tree1["a"],
                "a_2": zip_tree1["a"],
            }
        }
    }
