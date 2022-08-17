import io
from typing import (
    Iterable,
    Tuple,
)
from zipfile import ZipFile

import pytest
from tgmount import vfs, fs

from tgmount.zip import zips_as_dirs, zip_ls
from tgmount.zip.util import ZipTree

from ..helpers.zip import (
    ZipSourceTree,
    create_zip_from_tree,
    get_file_content_str_utf8,
    get_size,
)


@pytest.fixture
def zip_file1() -> Tuple[ZipFile, io.BytesIO]:
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


@pytest.fixture
def zip_tree1() -> ZipSourceTree:
    return {
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
