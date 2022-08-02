import os
import asyncio
import pyfuse3
import pyfuse3_asyncio

import pytest
from dataclasses import dataclass

from tgmount.fs import FileSystemOperations
from tgmount.vfs import DirLike, FileContentProto, root, vdir, vfile
from tgmount.vfs.dir import create_dir_content_from_tree, dir_content
from tgmount.vfs.file import text_content
from tgmount.vfs.types.dir import DirContent, DirContentItem, DirContentProto
from tgmount.vfs.types.file import FileContent

import multiprocessing
import threading
import subprocess

from .util import wait_for_mount, cleanup, umount
from .run import mountfs


@pytest.fixture()
def fs1():
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

    return FileSystemOperations(structure)


def test_fs1(tmpdir, fs1):
    print("test_fs1()")

    for f in mountfs(tmpdir, fs1):
        s = os.stat(f.tmpdir)

        print(f"ino={s.st_ino}")

        assert os.listdir(f.path(".")) == ["dir1", "dir2", "dir3"]
        assert os.listdir(f.path("dir1")) == ["file1.txt", "file2.txt"]
        assert os.listdir(f.path("dir2")) == ["file3.txt", "file4.txt", "dir2_dir3"]
        assert os.listdir(f.path("dir2", "dir2_dir3")) == [
            "file5.txt",
        ]
        assert os.listdir(f.path("dir3")) == ["dir3_file1.txt"]
