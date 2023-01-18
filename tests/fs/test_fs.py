import logging
import os

from ..helpers.fixtures_fs import fs_tree1
from ..helpers.fixtures_common import mnt_dir
from ..helpers.mountfs import mount_fs_tree_main
from ..helpers.spawn import spawn_fs_ops


def test_fs1(fs_tree1, mnt_dir):
    print("test_fs1()")

    for ctx in spawn_fs_ops(
        mount_fs_tree_main,
        {"debug": logging.INFO, "fs_tree": fs_tree1},
        mnt_dir=mnt_dir,
        min_tasks=10,
    ):

        assert os.listdir(ctx.path(".")) == ["dir1", "dir2", "dir3"]
        assert os.listdir(ctx.path("dir1")) == ["file1.txt", "file2.txt"]
        assert os.listdir(ctx.path("dir2")) == ["file3.txt", "file4.txt", "dir2_dir3"]
        assert os.listdir(ctx.path("dir2", "dir2_dir3")) == [
            "file5.txt",
        ]
        assert os.listdir(ctx.path("dir3")) == ["dir3_file1.txt"]
