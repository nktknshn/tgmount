import asyncio
from dataclasses import dataclass
import logging
import os
import threading
from typing import Iterable, Mapping, TypedDict

import pyfuse3
import pytest
import pytest_asyncio
import telethon
import tgmount.fs as fs
import tgmount.tgclient as tg
from tgmount.vfs import *
from tgmount import vfs
import tgmount.tg_vfs as tg_vfs
from telethon import events, types
from tests.helpers.tgclient import get_client_with_source
from tgmount.logging import init_logging
from tgmount.tgclient import guards

from ..helpers.asyncio import task_from_blocking, wait_ev, wait_ev_async
from ..helpers.spawn import MountContext, spawn_fs_ops

Message = telethon.tl.custom.Message
Document = telethon.types.Document
Client = tg.TgmountTelegramClient


@pytest.mark.asyncio
async def test_updates1(caplog):

    root1 = vfs.root(
        dir_content_from_tree(
            [
                vfile("file1.txt", text_content("blah"), extra=1),
                vfile("file2.txt", text_content("blah"), extra=2),
                vdir(
                    "dir1",
                    content=dir_content(
                        vfile("file3.txt", text_content("blah"), extra=3),
                        vfile("file4.txt", text_content("blah"), extra=4),
                    ),
                ),
            ]
        )
    )

    root2 = vfs.root(
        dir_content_from_tree(
            [
                vfile("file1.txt", text_content("blah"), extra=1),
                vfile("file2.txt", text_content("blah"), extra=666),
                vdir(
                    "dir1",
                    content=dir_content(
                        vfile("file3.txt", text_content("blah"), extra=3),
                        vfile("file4.txt", text_content("blah"), extra=777),
                    ),
                ),
            ]
        )
    )

    fs_ops = fs.FileSystemOperationsUpdatable(root1)

    fs_ops.update_root(root2)
