import os

from typing import TypedDict
from tgmount import vfs, fs

from ..helpers.fixtures import fs_tree1, mnt_dir
from ..helpers.spawn import spawn_fs_ops
from ..helpers.mountfs import mount_fs_tree_main


def test_fs1(fs_tree1, mnt_dir):
    print("test_fs1()")

    for ctx in spawn_fs_ops(
        mount_fs_tree_main,
        {"debug": True, "fs_tree": fs_tree1},
        mnt_dir=mnt_dir,
    ):
        s = os.stat(ctx.tmpdir)

        print(f"ino={s.st_ino}")

        assert os.listdir(ctx.path(".")) == ["dir1", "dir2", "dir3"]
        assert os.listdir(ctx.path("dir1")) == ["file1.txt", "file2.txt"]
        assert os.listdir(ctx.path("dir2")) == ["file3.txt", "file4.txt", "dir2_dir3"]
        assert os.listdir(ctx.path("dir2", "dir2_dir3")) == [
            "file5.txt",
        ]
        assert os.listdir(ctx.path("dir3")) == ["dir3_file1.txt"]
