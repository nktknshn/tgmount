import io
from typing import (
    Iterable,
    Tuple,
)
from zipfile import ZipFile

import pytest
from tgmount import vfs, fs

from tgmount.zip import zips_as_dirs, zip_ls

from ..helpers.zip import (
    ZipSourceTree,
    create_zip_from_tree,
    get_file_content_str_utf8,
    get_size,
)


def get_items_names(iter: Iterable[vfs.DirContentItem]):
    return list(map(lambda item: item.name, iter))


@pytest.mark.asyncio
async def test_zip():

    zf, zfdata = create_zip1()

    a = zip_ls(zf)

    assert isinstance(a, dict)
    assert set(a.keys()) == {"a"}

    a = zip_ls(zf, ["a"])

    assert isinstance(a, dict)
    assert len(a.keys()) == 4
    assert set(a.keys()) == {"b", "d", "a1.txt", "a2.txt"}


def create_zip1() -> Tuple[ZipFile, io.BytesIO]:
    """
    we will only rely on file pathes
    """

    data = io.BytesIO()
    zf = ZipFile(data, "w")

    # zf.writestr("/a/", "")
    # zf.writestr("/e/a1.txt", "somehow global path")
    zf.writestr("a/a1.txt", "hello gravity")
    zf.writestr("a/a2.txt", "hello moon")

    # zf.writestr("/a/b/", "")
    zf.writestr("a/b/a3.txt", "hello starts")
    zf.writestr("a/b/tvrdý.txt", "hello tvrdý")
    zf.writestr("a/b/русский файл.txt", "hello русский файл")

    # zf.writestr("/a/b/c/", "")
    zf.writestr("a/b/c/nested.txt", "hello time")

    zf.writestr("a/d/a_d.txt", "hello plants")

    # zf.filename = 'self.zip'

    zf.close()

    return zf, data


@pytest.mark.asyncio
async def test_create_zip_from_tree():
    z, d1 = create_zip1()
    z, d2 = create_zip_from_tree(
        {
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
    )

    assert d1.getbuffer() == d2.getbuffer()


@pytest.mark.asyncio
async def test_zip1(caplog):
    # caplog.set_level(logging.DEBUG)

    zf, zfdata = create_zip1()

    fc = vfs.file_content_from_io(zfdata)

    structure = vfs.root(
        zips_as_dirs(
            vfs.dir_content(vfs.vfile("archive.zip", fc)),
            skip_folder_if_single_subfolder=False,
        )
    )

    items = await vfs.dirlike_ls(structure, vfs.napp("/"))

    assert items
    assert get_items_names(items) == ["archive.zip"]
    assert isinstance(list(items)[0], vfs.DirLike)

    items = await vfs.dirlike_ls(structure, vfs.napp("/archive.zip/"))

    assert items
    assert get_items_names(items) == ["a"]
    assert isinstance(list(items)[0], vfs.DirLike)


@pytest.mark.asyncio
async def test_zip2():

    zf, zfdata = create_zip1()

    fc = vfs.file_content_from_io(zfdata)

    structure = vfs.root(
        zips_as_dirs(
            vfs.dir_content(vfs.vfile("archive.zip", fc)),
            skip_folder_if_single_subfolder=True,
        )
    )

    items = await vfs.dirlike_ls(structure, vfs.napp("/"))

    assert items
    assert get_items_names(items) == ["a"]
    assert isinstance(list(items)[0], vfs.DirLike)

    items = await vfs.dirlike_ls(structure, vfs.napp("/a"))

    assert items is not None
    assert len([*items]) == 4
    assert set(get_items_names(items)) == {"b", "d", "a1.txt", "a2.txt"}

    items = await vfs.dirlike_ls(structure, vfs.napp("/a/d"))

    assert items is not None
    assert len([*items]) == 1
    assert set(get_items_names(items)) == {"a_d.txt"}

    items = await vfs.dirlike_ls(structure, vfs.napp("/a/b"))

    assert items is not None
    assert len([*items]) == 4
    assert set(get_items_names(items)) == {
        "a3.txt",
        "tvrdý.txt",
        "русский файл.txt",
        "c",
    }

    items = await vfs.dirlike_ls(structure, vfs.napp("/a/b/c"))

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

    tree = await vfs.dir_content_get_tree(structure.content)

    t = await vfs.file_like_tree_map(tree, get_file_content_str_utf8)

    assert t == source_tree


@pytest.mark.asyncio
async def test_zip4():
    zf, zfdata = create_zip1()

    fc = vfs.file_content_from_io(zfdata)

    structure = vfs.root(
        zips_as_dirs(
            vfs.dir_content(vfs.vfile("archive.zip", fc)),
            skip_folder_if_single_subfolder=False,
        )
    )

    tree = await vfs.dir_content_get_tree(structure.content)

    t = await vfs.file_like_tree_map(tree, get_size)

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


@pytest.mark.asyncio
async def test_zip5():
    source_tree: ZipSourceTree = {
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
    }

    zf, zfdata = create_zip_from_tree(source_tree)

    structure = vfs.root(
        zips_as_dirs(
            vfs.dir_content(vfs.vfile("archive.zip", vfs.file_content_from_io(zfdata))),
            skip_folder_if_single_subfolder=True,
        )
    )

    tree = await vfs.dir_content_get_tree(structure.content)

    t = await vfs.file_like_tree_map(tree, get_file_content_str_utf8)

    assert t == {"archive.zip": source_tree}
