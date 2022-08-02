import os
import asyncio
import pyfuse3

import pyfuse3_asyncio

# from tgmount.vfs.greenback import pyfuse3_asyncio_greenback


from dataclasses import dataclass

from tgmount.fs import FileSystemOperations
from typing import Callable, Optional

import multiprocessing
import threading
import subprocess

from .util import wait_for_mount, cleanup, umount


@dataclass
class Fixtures:
    fs: FileSystemOperations
    tmpdir: str
    cross_process: Optional[object] = None

    def path(self, *p: str):
        return os.path.join(self.tmpdir, *p)


def run_fs(
    fs_ops: pyfuse3.Operations,
    destination: str,
):
    print("run_fs()")
    # event_loop = asyncio.get_event_loop()
    event_loop = asyncio.new_event_loop()
    event_loop.run_until_complete(
        _main(
            fs_ops,
            destination,
        )
    )
    # await pyfuse3.main(min_tasks=10)


# multiprocessing.get_context()


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


async def async_run_fs(
    fs_ops: pyfuse3.Operations,
    destination: str,
):
    print("run_fs()")
    # loop = asyncio.get_event_loop()

    await _main(
        fs_ops,
        destination,
    )
    # await pyfuse3.main(min_tasks=10)


def mountfs(tmpdir: str, fs: FileSystemOperations):
    print("mountfs()")
    mnt_dir = str(tmpdir)

    mp = multiprocessing.get_context("fork")

    with mp.Manager() as mgr:
        cross_process = mgr.Namespace()
        mount_process = mp.Process(target=run_fs, args=(fs, mnt_dir))

        mount_process.start()

        try:
            wait_for_mount(mount_process, mnt_dir)
            yield Fixtures(fs, mnt_dir, cross_process)
        except:
            cleanup(mount_process, mnt_dir)
            raise
        else:
            umount(mount_process, mnt_dir)


import sys


def spawn_process(
    proccess_function: Callable[
        [threading.Event, ...],
        None,
    ],
    mnt_dir: str,
    *args
):
    print("spawn_process()")

    mp = multiprocessing.get_context("spawn")
    with mp.Manager() as mgr:
        ev = mgr.Event()
        mount_process = mp.Process(
            target=proccess_function, args=(ev, *args), daemon=True
        )

        mount_process.start()

        try:
            wait_for_mount(mount_process, mnt_dir)
            yield ev, Fixtures(None, mnt_dir)
            # ev.set()
            # mount_process.join()
            # mount_process.close()

        except:
            cleanup(mount_process, mnt_dir)
            raise
        else:
            umount(mount_process, mnt_dir)
