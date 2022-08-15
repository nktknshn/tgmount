import os
import asyncio
import logging
from typing import Awaitable, Callable

import pytest
from tgmount import fs, vfs
from tgmount.logging import init_logging

from ..helpers.mountfs2 import mountfs, OnEventSetCallback


def main1(
    on_event: OnEventSetCallback,
):
    init_logging(True)

    root1 = vfs.root(
        vfs.create_dir_content_from_tree(
            {
                "subf": {
                    "aaa": vfs.text_content("aaaaaaa"),
                    "bbb": vfs.text_content("bbbbbbb"),
                }
            }
        )
    )

    root2 = vfs.root(
        vfs.create_dir_content_from_tree(
            {
                "subf": {
                    "ccc": vfs.text_content("ccccccc"),
                }
            }
        )
    )

    fs1 = fs.FileSystemOperationsUpdatable(root1)

    async def update():
        await fs1.update_root(root2)

    on_event(update)

    return fs1


@pytest.mark.asyncio
async def test_fs1(tmpdir, caplog):
    caplog.set_level(logging.DEBUG)

    for ctx in mountfs(main1, tmpdir):
        s = os.stat(ctx.tmpdir)

        print(f"ino={s.st_ino}")

        print("read 1")
        assert os.listdir(ctx.path("subf")) == ["aaa", "bbb"]

        ctx.cross_process_event.set()

        await asyncio.sleep(5)

        print("read 2")
        assert os.listdir(ctx.path("subf")) == ["ccc"]
