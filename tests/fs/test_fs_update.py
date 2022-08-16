import asyncio
import logging
import os
import threading
from typing import TypedDict

import pytest
from tgmount import fs, vfs
from tgmount.logging import init_logging

# from ..helpers.mountfs2 import OnEventSetCallback, mountfs
from ..helpers.spawn2 import GetProps, MountContext, OnEventCallbackSet, spawn_fs_ops
from ..helpers.fixtures import mnt_dir

Main1Props = TypedDict("Main1Props", debug=bool, ev0=threading.Event)


async def main1(
    props: Main1Props,
    on_event: OnEventCallbackSet,
):
    init_logging(props["debug"])

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

    on_event(props["ev0"], update)

    return fs1


@pytest.mark.asyncio
async def test_fs1(mnt_dir, caplog):
    caplog.set_level(logging.DEBUG)

    get_props: GetProps[Main1Props] = lambda ctx: {
        "debug": True,
        "ev0": ctx.mgr.Event(),
    }

    for ctx in spawn_fs_ops(
        main1,
        get_props,
        mnt_dir=mnt_dir,
    ):
        s = os.stat(ctx.tmpdir)

        print(f"ino={s.st_ino}")

        print("read 1")
        assert os.listdir(ctx.path("subf")) == ["aaa", "bbb"]
        assert ctx.props

        ctx.props["ev0"].set()

        await asyncio.sleep(1)

        print("read 2")
        assert os.listdir(ctx.path("subf")) == ["ccc"]
