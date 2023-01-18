import os
import random
from dataclasses import asdict, dataclass, field

from pprint import pprint
from typing import Any, Callable, Optional, TypedDict

import pytest
import pytest_asyncio
from telethon.tl.custom.message import File, Message
from typing_extensions import dataclass_transform

from tgmount import fs, vfs
from tgmount.config.types import Config

from tgmount.tgmount.error import TgmountError
from tgmount.tgmount.vfs_tree import VfsTree, VfsTreeDir

from ..config.fixtures import config_from_file
import pathvalidate


# source = DummyMessageSource()
# files_source = DummyFileSource()
# factory = FileFactoryDefault(files_source)


@pytest.mark.asyncio
async def test_vfs_tree1():
    tree = VfsTree()

    with pytest.raises(TgmountError) as e:
        await tree.get_dir("/")

    await tree.create_dir("/")
    root = await tree.get_dir("/")

    # tree.child_updated

    # tree.create_dir
    # tree.put_content
    # tree.put_dir
    # tree.remove_dir
    # tree.remove_content

    # tree.get_dir_content
    # tree.get_dir_content_items
    # tree.get_dir

    # tree.get_parent
    # tree.get_parents
    # tree.get_subdirs


@pytest.mark.asyncio
async def test_vfs_tree2():
    tree = VfsTree()

    root_dir = await tree.create_dir("/")
    my_mount = await root_dir.create_dir("/my-mount")

    await my_mount.create_dir("/all")
    await my_mount.create_dir("/messages")

    tmtc = await root_dir.create_dir("/tmtc")

    await tmtc.create_dir("/audio")
    await tmtc.create_dir("/video")

    tmtc_audio = await tmtc.get_subdir("/audio")

    file2 = vfs.text_file(f"file2.txt", "file2.txt content")

    await tmtc_audio.put_content(
        [
            vfs.text_file(f"file1.txt", "file1.txt content"),
            file2,
        ]
    )

    # print()
    # pprint(await tree.get_subdirs("/tmtc"))
    # dir_content = await tree.get_dir_content()
    # pprint(await vfs.dir_content_to_tree(dir_content))
    # await tmtc_audio.remove_content(file2)
    # pprint(await vfs.dir_content_to_tree(dir_content))
    # handle = await tree.get_handle("/")
    # root_dir = VfsTreePlainDir(
    #     handle,
    #     ProducerConfig(message_source=source, factory=factory, filters=[]),
    # )
    # await root_dir.produce()
