import os
import asyncio
import pyfuse3
import pyfuse3_asyncio

import pytest
from dataclasses import dataclass

from tgmount.fs import FileSystemOperations
from tgmount import vfs

from ..helpers.mountfs2 import mountfs
from .fixtures import fs_tree1


def fs1_main(fs_tree1):
    content: vfs.DirContent = vfs.create_dir_content_from_tree(fs_tree1)
    root = vfs.root(content)
    return FileSystemOperations(root)


def test_fs1(tmpdir, fs_tree1):
    print("test_fs1()")

    for ctx in mountfs(fs1_main, mnt_dir=tmpdir):
        s = os.stat(ctx.tmpdir)

        print(f"ino={s.st_ino}")

        assert os.listdir(ctx.path(".")) == ["dir1", "dir2", "dir3"]
        assert os.listdir(ctx.path("dir1")) == ["file1.txt", "file2.txt"]
        assert os.listdir(ctx.path("dir2")) == ["file3.txt", "file4.txt", "dir2_dir3"]
        assert os.listdir(ctx.path("dir2", "dir2_dir3")) == [
            "file5.txt",
        ]
        assert os.listdir(ctx.path("dir3")) == ["dir3_file1.txt"]
