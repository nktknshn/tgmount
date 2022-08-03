import asyncio
import errno
import functools
import logging
import os
import stat
import traceback
from functools import wraps
from typing import Any, Callable, List, Optional

import pyfuse3

logger = logging.getLogger("tgvfs")


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
