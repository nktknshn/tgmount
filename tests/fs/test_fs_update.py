import asyncio
import logging
import multiprocessing
import os
import threading
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Awaitable, Callable

import pyfuse3
import pyfuse3_asyncio
import pytest
import pytest_asyncio
from tgmount import fs, vfs
from tgmount.logging import init_logging

from .util import wait_for_mount, cleanup, umount
from .run import Fixtures


def task_from_blocking(blocking_func):
    return asyncio.create_task(
        asyncio.to_thread(blocking_func),
    )


def wait_ev(ev: threading.Event, on_done=lambda: None, event_id: str = ""):
    def _inner():
        ev.wait()
        on_done()

    return _inner


def mountfs_func(
    tmpdir: str,
    fs_func: Callable[[threading.Event, threading.Event, str], Awaitable[None]],
):
    mnt_dir = str(tmpdir)

    mp = multiprocessing.get_context("forkserver")

    with mp.Manager() as mgr:
        cross_process_event = mgr.Event()
        exit_event = mgr.Event()

        mount_process = mp.Process(
            target=run_fs,
            args=(
                fs_func,
                cross_process_event,
                exit_event,
                mnt_dir,
            ),
        )

        mount_process.start()

        try:
            wait_for_mount(mount_process, mnt_dir)
            yield Fixtures(
                None,
                mnt_dir,
                cross_process_event,
                exit_event,
            )
            exit_event.set()
        except:
            cleanup(mount_process, mnt_dir)
            raise
        else:
            umount(mount_process, mnt_dir)


def run_fs(
    fs_func: Callable[[threading.Event, threading.Event, str], Awaitable[None]],
    ev: threading.Event,
    exit_ev: threading.Event,
    destination: str,
):
    event_loop = asyncio.new_event_loop()
    event_loop.run_until_complete(
        fs_func(
            ev,
            exit_ev,
            destination,
        )
    )


async def _main(
    ev0: threading.Event,
    exit_event: threading.Event,
    destination: str,
):
    async def noop():
        return None

    env = {"on_event": noop}

    fs1 = main(lambda on_event: env.update({"on_event": on_event}))

    pyfuse3_asyncio.enable()

    fuse_options = set(pyfuse3.default_options)
    fuse_options.add("fsname=test_tgmount")
    # fuse_options.add("debug")

    pyfuse3.init(fs1, destination, fuse_options)

    pyfuse_task = asyncio.create_task(pyfuse3.main(min_tasks=10))

    wait_ev_task = task_from_blocking(wait_ev(ev0))

    async def on_event():
        await wait_ev_task
        await env["on_event"]()

    main_task = asyncio.create_task(
        asyncio.wait(
            [pyfuse_task, on_event()],
            return_when=asyncio.ALL_COMPLETED,
        )
    )

    def exit():
        ev0.set()
        pyfuse3.close(unmount=True)

    exit_ev_task = task_from_blocking(wait_ev(exit_event, exit))

    await asyncio.wait(
        [exit_ev_task, main_task],
        return_when=asyncio.FIRST_COMPLETED,
    )


class FileSystemOperationsUpdatable(fs.FileSystemOperations):
    def __init__(self, root: vfs.DirLike):
        super().__init__(root)

    def print_stats(self):
        print("inodes")
        print(self._inodes._inodes.keys())

        print("fhs")
        print(self._handers._fhs.keys())

    async def update_root(self, root: vfs.DirLike):

        for inode in reversed(self._inodes.get_inodes()):
            print(f"inode={inode}")
            kids = self._inodes.get_items_by_parent_dict(inode)

            if kids is None:
                continue

            for k, v in kids.items():
                print(f"invalidate_entry({inode}, {k})")
                pyfuse3.invalidate_entry_async(inode, k)

        # pyfuse3.invalidate_inode(pyfuse3.ROOT_INODE)

        # for inode in self._inodes._inodes.keys():
        #     pyfuse3.invalidate_inode(inode)

        self._init_handers(self._handers._last_fh + 1)
        self._init_root(root)

        print("update_root() done")


def main(
    on_event: Callable[[Callable[[], Awaitable[None]]], None],
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

    fs1 = FileSystemOperationsUpdatable(root1)

    async def update():
        await fs1.update_root(root2)

    on_event(update)

    return fs1


@pytest.mark.asyncio
async def test_fs1(tmpdir, caplog):
    caplog.set_level(logging.DEBUG)

    for ctx in mountfs_func(tmpdir, _main):
        s = os.stat(ctx.tmpdir)

        print(f"ino={s.st_ino}")

        print("read 1")
        assert os.listdir(ctx.path("subf")) == ["aaa", "bbb"]

        ctx.cross_process_event.set()

        await asyncio.sleep(5)

        print("read 2")
        assert os.listdir(ctx.path("subf")) == ["ccc"]
