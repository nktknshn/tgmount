import logging
import os
import pytest
from tests.helpers.mocked.mocked_storage import StorageEntity

from pprint import pprint
from tgmount import vfs, zip as z
from tests.integrational.helpers import mdict
from tests.integrational.integrational_configs import create_config
from tgmount.tglog import init_logging
from tgmount.tgmount.vfs_tree import VfsTree, VfsTreeDir
from tgmount.tgmount.vfs_tree_types import (
    TreeEventNewDirs,
    TreeEventNewItems,
    TreeEventRemovedDirs,
)
from tgmount.tgmount.wrappers.wrapper_exclude_empty_dirs import WrapperEmpty

from .fixtures import *
from .context import Context

from ..logger import logger as _logger

import tgmount


class TreeListener:
    logger = _logger.getChild("TreeListener")

    def __init__(self, tree: VfsTree) -> None:
        self.tree = tree
        self.updates = []

        tree.subscribe(self._on_update)

    async def _on_update(self, tree, updates):
        self.logger.debug(f"_on_update({updates})")
        self.updates.extend(updates)

    def pop(self):
        _updates = self.updates
        self.updates = []
        return _updates


@pytest.mark.asyncio
async def test_wrapper1(caplog):
    t = VfsTree()
    listener = TreeListener(t)

    d1 = await t.create_dir("/")
    dc1 = await d1.get_dir_content()

    d1.add_wrapper(WrapperEmpty(d1))

    assert await vfs.dir_content_read(dc1) == []

    f1, f2 = [
        vfs.text_file("file1.txt", "123"),
        vfs.text_file("file2.txt", "123"),
    ]

    await d1.put_content([f1, f2])
    assert await vfs.dir_content_read(dc1) == [f1, f2]
    listener.pop()

    sd1 = await d1.create_dir("subdir1")

    # create_dir shouldn't generate event
    assert listener.pop() == []

    assert await vfs.dir_content_read(dc1) == [f1, f2]

    sd1f1 = vfs.text_file("file1.txt", "123")

    await sd1.put_content([sd1f1])

    # now the folder should appear
    assert listener.pop() == [
        TreeEventNewDirs(sender=d1, update_path=d1.path, new_dirs=[sd1.path]),
        TreeEventNewItems(sender=sd1, update_path=sd1.path, new_items=[sd1f1]),
    ]

    assert (await vfs.dir_content_read_dict(dc1)).keys() == {
        f1.name,
        f2.name,
        sd1.name,
    }

    await sd1.remove_content(sd1f1)

    # now the folder should disappear
    assert listener.pop() == [
        TreeEventRemovedDirs(sender=d1, update_path=d1.path, removed_dirs=[sd1.path]),
    ]

    assert (await vfs.dir_content_read_dict(dc1)).keys() == {
        f1.name,
        f2.name,
    }


async def read_dir(d: VfsTreeDir):
    return await vfs.dir_content_read_dict(await d.get_dir_content())


@pytest.mark.asyncio
async def test_wrapper_nested_wrappers(caplog):
    # init_logging(logging.DEBUG)
    # caplog.set_level(logging.DEBUG)

    t = VfsTree()
    listener = TreeListener(t)

    d1 = await t.create_dir("/")
    listener.pop()

    d1.add_wrapper(WrapperEmpty(d1))

    sd1 = await d1.create_dir("subdir1")
    sd1.add_wrapper(WrapperEmpty(sd1))

    assert listener.pop() == []

    ssd1 = await sd1.create_dir("subsubdir1")
    ssd1.add_wrapper(WrapperEmpty(ssd1))

    assert listener.pop() == []

    assert (await read_dir(d1)).keys() == set()

    sd1f1 = vfs.text_file("file1.txt", "123")
    await ssd1.put_content(sd1f1)

    # /subdir1 and /subdir1/subsubdir1 shoueld appear in events

    assert listener.pop() == [
        TreeEventNewDirs(sender=d1, update_path=d1.path, new_dirs=[sd1.path]),
        TreeEventNewDirs(sender=sd1, update_path=sd1.path, new_dirs=[ssd1.path]),
        TreeEventNewItems(sender=ssd1, update_path=ssd1.path, new_items=[sd1f1]),
    ]

    await ssd1.remove_content(sd1f1)

    assert listener.pop() == [
        TreeEventRemovedDirs(sender=d1, update_path=d1.path, removed_dirs=[sd1.path]),
    ]

    sssd1 = await ssd1.create_dir("subsubsubdir1")

    assert listener.pop() == []

    await sssd1.put_content(sd1f1)

    assert listener.pop() == [
        TreeEventNewDirs(sender=d1, update_path=d1.path, new_dirs=[sd1.path]),
        TreeEventNewDirs(sender=sd1, update_path=sd1.path, new_dirs=[ssd1.path]),
        TreeEventNewDirs(sender=ssd1, update_path=ssd1.path, new_dirs=[sssd1.path]),
        TreeEventNewItems(sender=sssd1, update_path=sssd1.path, new_items=[sd1f1]),
    ]
