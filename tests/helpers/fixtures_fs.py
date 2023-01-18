import pytest

from tgmount import vfs


@pytest.fixture()
def fs_tree1() -> vfs.DirContentSourceMapping:
    tc = vfs.text_content
    return {
        "dir1": {
            "file1.txt": tc("file1.txt content"),
            "file2.txt": tc("file2.txt content"),
        },
        "dir2": {
            "file3.txt": tc("file3.txt content"),
            "file4.txt": tc("file4.txt content"),
            "dir2_dir3": {
                "file5.txt": tc("file5.txt content"),
            },
        },
        "dir3": vfs.dir_content(
            vfs.vfile("dir3_file1.txt", tc("dir3_file1.txt content"))
        ),
    }
