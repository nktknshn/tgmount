import asyncio
import logging
import os
import threading
from typing import Mapping, TypedDict

import pytest
from tgmount import fs, vfs
from tgmount.tglog import init_logging
from tgmount.util import none_fallback

from ..helpers.spawn import GetProps, OnEventCallbackSet, spawn_fs_ops
from ..helpers.fixtures import mnt_dir

from pprint import pprint

Main1Props = TypedDict("Main1Props", debug=bool, ev0=threading.Event)

dirc = vfs.dir_content_from_source
root = vfs.root


async def main1(
    props: Main1Props,
    on_event: OnEventCallbackSet,
):
    init_logging(props["debug"])

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

    root2 = vfs.root(
        vfs.dir_content_from_source(
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

    for ctx in spawn_fs_ops(main1, get_props, mnt_dir=mnt_dir, min_tasks=10):
        s = os.stat(ctx.tmpdir)

        print(f"ino={s.st_ino}")

        print("read 1")
        assert os.listdir(ctx.path("subf")) == ["aaa", "bbb"]
        assert ctx.props

        ctx.props["ev0"].set()

        await asyncio.sleep(1)

        print("read 2")
        assert os.listdir(ctx.path("subf")) == ["ccc"]


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
async def test_fs2(mnt_dir, caplog):
    caplog.set_level(logging.INFO)

    root1 = root(
        {
            "d1": [f("a"), f("b")],
            "d2": {"d3": [f("c"), f("d")]},
            "d3": {
                "d3": {
                    "d3": {
                        "d3": {
                            "d3": [f("c"), f("d"), f("e")],
                        },
                    },
                },
            },
        }
    )

    root2 = root(
        {
            "d1": [f("c"), f("b")],
            "d2": {},
            "d3": {
                "d3": {
                    "d3": {
                        "d3": {
                            "d3": [f("c"), f("e")],
                        },
                    },
                },
            },
        },
    )

    root3 = root(
        {
            "d1": [f("c"), f("b")],
            "d2": [f("a"), f("b")],
        },
    )

    async def main(props: Mapping, on_event: OnEventCallbackSet):
        init_logging(props["debug"])
        fs1 = fs.FileSystemOperationsUpdatable(root1)
        print_inodes = async_lambda(
            lambda: pprint(fs1.inodes.get_inodes_with_paths_str())
        )
        on_event(props["ev0"], lambda: fs1.update_root(root2))
        on_event(props["print_inodes"], print_inodes)
        on_event(props["print_inodes1"], print_inodes)
        on_event(props["ev2"], lambda: fs1.update_root(root3))
        return fs1

    for ctx in spawn_fs_ops(
        main,
        lambda ctx: {
            "debug": False,
            "ev0": ctx.mgr.Event(),
            "print_inodes": ctx.mgr.Event(),
            "print_inodes1": ctx.mgr.Event(),
            "ev2": ctx.mgr.Event(),
        },
        mnt_dir=mnt_dir,
        min_tasks=10,
    ):
        for a in os.walk(mnt_dir):
            pass

        ctx.props["print_inodes"].set()  # type: ignore

        assert ctx.listdir("d1") == {"a", "b"}

        ctx.props["ev0"].set()  # type: ignore

        await asyncio.sleep(0.1)
        assert ctx.listdir("d1") == {"c", "b"}

        with pytest.raises(FileNotFoundError) as e_info:
            ctx.listdir("d2/d3")

        assert ctx.exists("d2/d3") == False
        assert ctx.exists("d1/a") == False

        ctx.props["ev2"].set()  # type: ignore

        ctx.props["print_inodes1"].set()  # type: ignore

        # os.walk(mnt_dir)
