import pyfuse3
import pytest
from tgmount.fs import FileSystemOperations
from tgmount.vfs import root, vfile
from tgmount.vfs.dir import create_dir_content_from_tree, dir_content
from tgmount.vfs.file import text_content
from tgmount.vfs.types.dir import DirContent


@pytest.mark.asyncio
async def test_fs_operations1():
    content: DirContent = create_dir_content_from_tree(
        {
            "dir1": {
                "file1.txt": "file1.txt content",
                "file2.txt": "file2.txt content",
            },
            "dir2": {
                "file3.txt": "file3.txt content",
                "file4.txt": "file4.txt content",
                "dir2_dir3": {
                    "file5.txt": "file5.txt content",
                },
            },
            "dir3": dir_content(
                vfile("dir3_file1.txt", text_content("dir3_file1.txt content"))
            ),
        }
    )

    structure = root(content)

    fs = FileSystemOperations(structure)

    root_attrs = await fs.lookup(pyfuse3.ROOT_INODE, b".")

    assert root_attrs.st_ino == pyfuse3.ROOT_INODE
