import os
from typing import Any, Callable, Optional
from typing_extensions import dataclass_transform

import random
from dataclasses import dataclass, field
import pytest
import pytest_asyncio
from telethon.tl.custom.message import Message, File
from tgmount.config.types import Config
from tgmount.tg_vfs.classifier import ClassifierProto
from tgmount.tg_vfs.types import FileContentProviderProto
from tgmount.tgclient.client import TgmountTelegramClient
from tgmount.tgclient.message_source import (
    MessageSourceSubscribable,
    Subscribable,
    TelegramMessageSource,
    TelegramMessageSourceSimple,
)
from tgmount.tgmount.builderbase import TgmountBuilderBase
from tgmount.tgmount.error import TgmountError
from tgmount.tgmount.types import CreateRootResources
from tgmount.tgmount.builder import TgmountBuilder

from tgmount.tgmount.vfs_structure import VfsStructure
from tgmount.tgmount.vfs_structure_producer2 import VfsStructureFromConfigProducer

from tgmount import vfs
from tgmount.tgmount.vfs_structure_types import VfsStructureProto

from ..config.fixtures import config_from_file
from ..helpers.dummy_classes import *


msg = DummyMessage

messages = [
    msg(text="aaa", username="user1"),
    msg(text="aaa", username="user1"),
    msg(text="aaa", username="user1", file=DummyFile("abcded.txt")),
    msg(text="aaa", username="user2"),
    msg(text="aaa", username="user2"),
    msg(text="aaa", username="user2", file=DummyFile("abcded.txt")),
]


@pytest.mark.asyncio
async def test_vfs_structure():
    vs1 = VfsStructure()
    vs2 = VfsStructure()

    await vs1.put("/", [vfs.text_file("file1", "")])
    await vs1.put("/", [vfs.text_file("file2", "")])

    await vs2.put("/", [vfs.text_file("file4", "")])

    await vs1.put("/subdir1", vs2)
    await vs1.put("/subdir1", [vfs.text_file("file3", "")])


async def ls_struct(vs: VfsStructureProto, path: str):
    npath = vfs.napp(path, noslash=True)

    for p in npath:
        (subdirs, content) = await vs.list_content()
        if (_vs := subdirs.get(p)) is None:
            raise TgmountError(f"Missing {p} in {vs}")
        else:
            vs = _vs

    return await vs.list_content()


async def print_struct(vs: VfsStructureProto, path: str):
    (subdirs, content) = await ls_struct(vs, path)

    print(path)
    print(f"dirs: {list(subdirs.keys())}")
    print(f"content: {content}")


class UpdatesListener:
    def __init__(self) -> None:
        self.updates = []

    async def on_update(self, source, update):
        self.updates.append(update)
        # print(f"UPDATE: {source} {update}")

    async def pop_update(self):
        return self.updates.pop(0)


@pytest.mark.asyncio
async def test_vfs_producer(config_from_file):
    print()

    cfg_dict = Config.from_yaml(config_from_file)

    builder = DummyTgmountBuilder()
    resources = await builder.create_resources(cfg_dict)

    source_mymount = builder.get_source("my-mount")
    source_tmtc = builder.get_source("tmtc")

    updates = UpdatesListener()

    await source_mymount.set_messages({messages[0], messages[1]})

    await source_tmtc.set_messages(
        {
            messages[0],
            messages[2],
            messages[3],
            messages[4],
            messages[5],
        }
    )

    producer = VfsStructureFromConfigProducer.from_config(
        resources=resources, dir_config=cfg_dict.root.content
    )

    async def print_update(source, update):
        print(f"UPDATE: {source} {update}")

    producer.subscribe(print_update)
    producer.subscribe(updates.on_update)

    await producer.produce_vfs_struct()
    struct = producer.get_vfs_structure()

    await print_struct(struct, "/tmtc/by-sender/")
    await print_struct(struct, "/tmtc/by-sender/user1")

    await source_tmtc.set_messages(
        {
            messages[0],
            messages[2],
            messages[3],
            messages[4],
            messages[5],
        }
    )

    await print_struct(struct, "/tmtc/by-sender/user1")
    await print_struct(struct, "/tmtc/by-sender/user2")

    await source_tmtc.set_messages({messages[0], messages[1]})

    await print_struct(struct, "/my-mount/")
    await print_struct(struct, "/tmtc/by-sender/user1")
    # await print_struct(struct, "/tmtc/by-sender/user2")
