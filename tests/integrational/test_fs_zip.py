import io
import os
from zipfile import ZipFile

import pytest
from tgmount import fs, vfs, zip

from ..helpers.spawn import spawn_fs_ops
from ..helpers.mountfs import mount_fs_tree_main
from ..helpers.zip import ZipSourceTree, create_zip_from_tree
from ..helpers.fixtures import mnt_dir

# import tgmount.fs as fs
# import tgmount.vfs as vfs
# import tgmount.zip as z
# from tgmount.logging import init_logging
# from tgmount.vfs.file import file_content_from_file, file_content_from_io

# from .util import ZipSourceTree, create_zip_from_tree


Zip1Fixture = tuple[bytes, ZipFile, io.BytesIO]


@pytest.fixture
def mp3bytes1() -> bytes:
    with open("tests/fixtures/files/Tvrdý _ Havelka - Žiletky.mp3", mode="rb") as f:
        return f.read()


@pytest.fixture
def zip_tree1(mp3bytes1) -> ZipSourceTree:

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
                    "Tvrdý _ Havelka - Žiletky.mp3": mp3bytes1,
                },
            },
            "d": {"a_d.txt": "hello plants"},
        }
    }


def test_fs_zip1(mnt_dir: str, zip_tree1: ZipSourceTree):
    (zf, zb) = create_zip_from_tree(zip_tree1)

    fs_tree: vfs.DirContentSourceTree = {
        "dir1": {
            "file1.txt": vfs.text_content("file1.txt content"),
            "file2.txt": vfs.text_content("file2.txt content"),
        },
        "telegram": {"channel 010101": {"music.zip": vfs.file_content_from_io(zb)}},
    }

    for m in spawn_fs_ops(
        mount_fs_tree_main,
        {"debug": False, "fs_tree": fs_tree},
        mnt_dir=mnt_dir,
    ):

        assert os.listdir(m.path(".")) == ["dir1", "telegram"]

        with open(m.path("telegram/channel 010101/music.zip"), "rb") as f:
            assert f.read() == zb.getbuffer()


# def test_fs_zip2(tmpdir: str, zip_tree1: ZipSourceTree, mp3bytes1: bytes):
#     (zf, zb) = create_zip_from_tree(zip_tree1)

#     vfs_root = vfs.root(
#         z.zips_as_dirs(
#             vfs.dir_from_tree(
#                 {
#                     "dir1": {
#                         "file1.txt": "file1.txt content",
#                         "file2.txt": "file2.txt content",
#                     },
#                     "telegram": {
#                         "channel 010101": {"music.zip": file_content_from_io(zb)}
#                     },
#                 }
#             )
#         )
#     )

#     for m in mountfs(tmpdir, fs.FileSystemOperations(vfs_root)):
#         assert os.listdir(m.path("telegram/channel 010101/music.zip")) == ["a"]
#         assert os.listdir(m.path("telegram/channel 010101/music.zip/a")) == [
#             "a1.txt",
#             "a2.txt",
#             "b",
#             "d",
#         ]

#         with open(
#             m.path(
#                 "telegram/channel 010101/music.zip/a/b/c/Tvrdý _ Havelka - Žiletky.mp3"
#             ),
#             "rb",
#         ) as f:
#             assert f.read() == mp3bytes1


# class Ops(fs.FileSystemOperations):
#     def __init__(self, root: vfs.DirLike):
#         super().__init__(root)

#         self.read_by_fh: dict[int, list[tuple[int, int]]] = {}

#     async def read(self, fh, off, size):

#         if fh not in self.read_by_fh:
#             self.read_by_fh[fh] = []

#         self.read_by_fh[fh].append((off, size))

#         print(self.read_by_fh)

#         return await super().read(fh, off, size)


# def test_fs_zip3(tmpdir: str, zip_tree1: ZipSourceTree, mp3bytes1: bytes):
#     (zf, zb) = create_zip_from_tree(
#         {
#             "Tvrdý _ Havelka - Žiletky.mp3": mp3bytes1,
#         }
#     )

#     init_logging(True)

#     vfs_root = vfs.root(
#         z.zips_as_dirs(vfs.dir_from_tree({"music.zip": file_content_from_io(zb)}))
#     )

#     ops = Ops(vfs_root)

#     for m in mountfs(tmpdir, ops):
#         with open(
#             m.path("music.zip/Tvrdý _ Havelka - Žiletky.mp3"),
#             "rb",
#         ) as f:
#             assert f.read(1024 * 10) == mp3bytes1[: 1024 * 10]
