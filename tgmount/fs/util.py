import asyncio
import errno
import functools
import logging
import os
import stat
import traceback
from functools import wraps
from typing import Any, Callable, List, Optional, overload
import time

import pyfuse3

# logger = logging.getLogger("tgvfs")

# from tgmount import tglog


def measure_time_sync(*, logger_func):
    def measure_time(func):
        @wraps(func)
        def inner_function(*args, **kwargs):
            started = time.time_ns()
            res = func(*args, **kwargs)
            duration = time.time_ns() - started

            logger_func(f"{func} = {int(duration/1000/1000)} ms")

            return res

        return inner_function

    return measure_time


def measure_time(*, logger_func):
    def measure_time(func):
        @wraps(func)
        async def inner_function(*args, **kwargs):
            started = time.time_ns()
            res = await func(*args, **kwargs)
            duration = time.time_ns() - started

            logger_func(f"{func} = {int(duration/1000/1000)} ms")

            return res

        return inner_function

    return measure_time


def exception_handler(func):
    @wraps(func)
    async def inner_function(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except pyfuse3.FUSEError:
            raise
        except Exception:
            logger.error(traceback.format_exc())
            raise pyfuse3.FUSEError(errno.EIO)

    return inner_function


def create_file_attributes(
    size: int,
    perms=0o644,
    stamp: int = int(1438467123.985654 * 1e9),
    inode: Optional[int] = None,
):
    return create_attributes(
        size=size,
        stamp=stamp,
        st_mode=(stat.S_IFREG | perms),
        inode=inode,
    )


def create_directory_attributes(
    # inode: int,
    inode: int,
    perms=0o755,
    stamp: int = int(1438467123.985654 * 1e9),
):
    return create_attributes(
        size=0, stamp=stamp, st_mode=(stat.S_IFDIR | perms), inode=inode
    )


def create_attributes(st_mode: int, stamp: int, size: int, inode: Optional[int] = None):
    attrs = pyfuse3.EntryAttributes()
    #
    # if not directory:
    #     attrs.st_mode = (stat.S_IFREG | 0o644)
    # else:
    #     attrs.st_mode = (stat.S_IFDIR | 0o755)
    attrs.st_mode = st_mode
    attrs.st_size = size

    stamp = stamp

    attrs.st_atime_ns = stamp
    attrs.st_ctime_ns = stamp
    attrs.st_mtime_ns = stamp

    attrs.st_gid = os.getgid()
    attrs.st_uid = os.getuid()

    if inode is not None:
        attrs.st_ino = inode

    return attrs


@overload
def str_to_bytes(s: str) -> bytes:
    ...


@overload
def str_to_bytes(s: list[str]) -> list[bytes]:
    ...


def str_to_bytes(s: str | list[str]) -> bytes | list[bytes]:
    if isinstance(s, list):
        return list(map(str_to_bytes, s))

    return s.encode("utf-8")


@overload
def bytes_to_str(bs: bytes) -> str:
    ...


@overload
def bytes_to_str(bs: list[bytes]) -> list[str]:
    ...


def bytes_to_str(bs: bytes | list[bytes]) -> str | list[str]:
    if isinstance(bs, list):
        return list(map(lambda b: b.decode("utf-8"), bs))

    return bs.decode("utf-8")
