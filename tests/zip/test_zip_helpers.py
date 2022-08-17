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

from .fixtures import zip_file1, zip_tree1


@pytest.mark.asyncio
async def test_create_zip_from_tree(zip_file1, zip_tree1):
    z, d1 = zip_file1
    z, d2 = create_zip_from_tree(zip_tree1)

    assert d1.getbuffer() == d2.getbuffer()
