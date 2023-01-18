import asyncio
import logging
import os
import threading
from typing import TypedDict

import pytest

from tgmount import fs, vfs
from tgmount.tglog import init_logging
from tgmount.util import none_fallback

from ..helpers.fixtures_common import mnt_dir
from ..helpers.spawn import GetProps, OnEventCallbackSet, spawn_fs_ops

Main1Props = TypedDict("Main1Props", debug=int, ev0=threading.Event)

dirc = vfs.dir_content_from_source
root = vfs.root


def f(name: str, content=None):
    return vfs.vfile(
        name, content=none_fallback(content, vfs.text_content("we dont care"))
    )


def d(name: str, content):
    return vfs.vdir(name, content=content)


def async_lambda(f):
    async def _inner():
        f()

    return _inner


@pytest.mark.asyncio
async def test_fs1(mnt_dir, caplog):

    # caplog.set_level(logging.DEBUG)

    get_props: GetProps[Main1Props] = lambda ctx: {
        "debug": logging.CRITICAL,
        "ev0": ctx.mgr.Event(),
    }

    root1 = vfs.root(
        vfs.dir_content_from_source(
            {
                "subf": {
                    "aaa": vfs.text_content("aaaaaaa"),
                    "bbb": vfs.text_content("bbbbbbb"),
                }
            }
        )
    )

    async def main1(
        props: Main1Props,
        on_event: OnEventCallbackSet,
    ):
        init_logging(props["debug"])

        fs1 = fs.FileSystemOperationsUpdatable(root1)

        async def update():
            await fs1.update(
                fs.FileSystemOperationsUpdate(
                    removed_files=[
                        "/subf/aaa",
                        "/subf/bbb",
                    ],
                    new_files={
                        "/subf/ccc": vfs.text_file("ccc", "ccc content"),
                    },
                )
            )

        on_event(props["ev0"], update)

        return fs1

    for ctx in spawn_fs_ops(main1, get_props, mnt_dir=mnt_dir, min_tasks=10):
        s = os.stat(ctx.tmpdir)

        assert os.listdir(ctx.path("subf")) == ["aaa", "bbb"]
        assert ctx.props

        ctx.props["ev0"].set()

        # await asyncio.sleep(1)

        assert os.listdir(ctx.path("subf")) == ["ccc"]
