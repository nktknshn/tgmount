import pyfuse3
import pytest
from tgmount.fs import FileSystemOperations

from tgmount import vfs

from ..helpers.fixtures import fs_tree1


@pytest.mark.asyncio
async def test_fs_operations1(fs_tree1: vfs.DirContentSourceMapping):

    structure = vfs.root(
        vfs.dir_content_from_source(fs_tree1),
    )

    fs = FileSystemOperations(structure)

    root_attrs = await fs.lookup(pyfuse3.ROOT_INODE, b".")

    assert root_attrs.st_ino == pyfuse3.ROOT_INODE
