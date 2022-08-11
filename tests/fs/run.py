import os
import asyncio
import queue
import pyfuse3

import pyfuse3_asyncio

# from tgmount.vfs.greenback import pyfuse3_asyncio_greenback


from dataclasses import dataclass

from tgmount import fs
from typing import Any, AsyncGenerator, Awaitable, Callable, Generator, Optional

import multiprocessing
import threading
import subprocess

from .util import wait_for_mount, cleanup, umount


@dataclass
class Fixtures:
    fs: fs.FileSystemOperations
    tmpdir: str
    cross_process_event: Optional[threading.Event] = None
    exit_event: Optional[threading.Event] = None

    def path(self, *p: str):
        return os.path.join(self.tmpdir, *p)


def mountfs(tmpdir: str, fs: fs.FileSystemOperations):
    print("mountfs()")
    mnt_dir = str(tmpdir)

    mp = multiprocessing.get_context("fork")

    with mp.Manager() as mgr:
        cross_process = mgr.Namespace()
        cross_process_queue = mgr.Queue()
        cross_process_value = None
        cross_process_event = mgr.Event()

        # cross_process_value = mgr.Value(FileSystemOperations, fs)

        mount_process = mp.Process(target=run_fs, args=(fs, mnt_dir))

        mount_process.start()

        try:
            wait_for_mount(mount_process, mnt_dir)
            yield Fixtures(fs, mnt_dir, cross_process_event)
        except:
            cleanup(mount_process, mnt_dir)
            raise
        else:
            umount(mount_process, mnt_dir)


async def _main(fs_ops: pyfuse3.Operations, destination: str, debug=True):
    print("_main()")

    # pyfuse3_asyncio_greenback.enable()
    pyfuse3_asyncio.enable()

    fuse_options = set(pyfuse3.default_options)
    fuse_options.add("fsname=test_tgmount")

    # if debug:
    #     fuse_options.add("debug")

    pyfuse3.init(fs_ops, destination, fuse_options)
    await pyfuse3.main(min_tasks=10)


def run_fs(
    fs_ops: pyfuse3.Operations,
    destination: str,
):
    print("run_fs()")
    event_loop = asyncio.new_event_loop()
    event_loop.run_until_complete(
        _main(
            fs_ops,
            destination,
        )
    )


async def mountfs_func(
    tmpdir: str,
    fs_func: Callable[[threading.Event], AsyncGenerator[fs.FileSystemOperations, Any]],
):
    print("mountfs()")
    mnt_dir = str(tmpdir)

    mp = multiprocessing.get_context("fork")

    with mp.Manager() as mgr:
        cross_process = mgr.Namespace()
        cross_process_event = mgr.Event()
        cross_process_queue = mgr.Queue()
        cross_process_value = None
        # cross_process_value = mgr.Value(FileSystemOperations, fs)

        async for fs in fs_func(cross_process_event):
            mount_process = mp.Process(target=run_fs, args=(fs, mnt_dir))

            mount_process.start()

            try:
                wait_for_mount(mount_process, mnt_dir)
                yield Fixtures(fs, mnt_dir, cross_process_event)
            except:
                cleanup(mount_process, mnt_dir)
                raise
            else:
                umount(mount_process, mnt_dir)
