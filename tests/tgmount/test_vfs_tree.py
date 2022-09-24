import os
from typing import Any, Callable, Optional, TypedDict
from typing_extensions import dataclass_transform

import random
from dataclasses import dataclass, field, asdict
import pytest
import pytest_asyncio
from telethon.tl.custom.message import Message, File
from tgmount.config.types import Config
from tgmount.fs.util import measure_time
from tgmount.tg_vfs.classifier import ClassifierProto
from tgmount.tg_vfs.filefactorybase import FileFactoryDefault
from tgmount.tg_vfs.tree.helpers.remove_empty import remove_empty_dirs_content
from tgmount.tg_vfs.types import FileContentProviderProto
from tgmount.tgclient.client import TgmountTelegramClient
from tgmount.tgclient.message_source import (
    MessageSourceSubscribable,
    Subscribable,
    TelegramMessageSource,
    TelegramMessageSourceSimple,
)
from tgmount.tgmount.builder import TgmountBuilder
from tgmount.tgmount.builderbase import TgmountBuilderBase
from tgmount.tgmount.error import TgmountError
from tgmount.tgmount.provider_sources import (
    SourcesProvider,
)
from tgmount.tgmount.types import CreateRootResources

from tgmount.tgmount.vfs_structure import VfsStructure
from tgmount.tgmount.vfs_structure_producer2 import VfsStructureFromConfigProducer

from tgmount import vfs
from tgmount.tgmount.vfs_structure_types import VfsStructureProto

from ..config.fixtures import config_from_file
from ..helpers.dummy_classes import *
from tgmount.tgmount.vfs_structure_producer3 import *

# source = DummyMessageSource()
# files_source = DummyFileSource()

# factory = FileFactoryDefault(files_source)
from pprint import pprint


@pytest.mark.asyncio
async def test_vfs_tree(config_from_file):
    tree = VfsTree()

    root_dir = await tree.create_dir("/")

    my_mount = await root_dir.create_dir("/my-mount")

    await my_mount.create_dir("/all")
    await my_mount.create_dir("/messages")

    tmtc = await root_dir.create_dir("/tmtc")

    await tmtc.create_dir("/audio")
    await tmtc.create_dir("/video")

    tmtc_audio = await tmtc.get_subdir("/audio")

    file2 = vfs.text_file(f"file2.txt", "file2.txt content")
    await tmtc_audio.put_content(
        [
            vfs.text_file(f"file1.txt", "file1.txt content"),
            file2,
        ]
    )

    print()

    # pprint(await tree.get_subdirs("/tmtc"))

    dir_content = await tree.get_dir_content()

    pprint(await vfs.dir_content_to_tree(dir_content))

    await tmtc_audio.remove_content(file2)

    pprint(await vfs.dir_content_to_tree(dir_content))

    # handle = await tree.get_handle("/")

    # root_dir = VfsTreePlainDir(
    #     handle,
    #     ProducerConfig(message_source=source, factory=factory, filters=[]),
    # )

    # await root_dir.produce()


msg = DummyMessage

messages = [
    msg(text="aaa", username="user1"),
    msg(text="aaa", username="user1"),
    msg(text="aaa", username="user1", file=DummyFile("abcded.txt")),
    msg(text="aaa", username="user2"),
    msg(text="aaa", username="user2"),
    msg(text="aaa", username="user2", file=DummyFile("abcded.txt")),
    # msg(username="user2", file=DummyFile("some_archive.zip")),
]

# Update = TypedDict(update=)


@pytest.mark.asyncio
async def test_vfs_tree2(config_from_file):
    print()

    cfg_dict = Config.from_yaml(config_from_file)

    builder = DummyTgmountBuilder()
    client = await builder.create_client(cfg_dict)
    resources = await builder.create_resources(client, cfg_dict)

    source_mymount = builder.get_source("my-mount")
    source_tmtc = builder.get_source("tmtc")

    await source_mymount.set_messages({messages[0], messages[1]})
    await source_tmtc.set_messages({messages[0], messages[2]})

    tree = VfsTree()

    async def print_update(provider, source, updates: list[UpdateType]):

        update = fs.FileSystemOperationsUpdate()

        for u in updates:
            path = u.update_path

            if isinstance(u, UpdateRemovedItems):
                for item in u.removed_items:
                    update.removed_files.append(os.path.join(path, item.name))
            elif isinstance(u, UpdateNewItems):
                for item in u.new_items:
                    update.new_files[os.path.join(path, item.name)] = item
            elif isinstance(u, UpdateRemovedDirs):
                for path in u.removed_dirs:
                    update.removed_dir_contents.append(path)
            elif isinstance(u, UpdateNewDirs):
                for path in u.new_dirs:
                    update.new_dirs[path] = await tree.get_dir_content(path)

            # for item in asdict(u).get("removed_items", []):
            #     update.removed_files.append(os.path.join(path, item.name))

            # for item in asdict(u).get("new_items", []):
            #     update.new_files[os.path.join(path, item.name)] = item

            # for path in asdict(u).get("removed_dirs", []):
            #     update.removed_dir_contents.append(path)

            # for path in asdict(u).get("new_dirs", []):
            #     update.new_dirs[path] = await tree.get_dir_content(path)

        pprint(f"UPDATE: {provider} {source} {update}")

    source_provider = SourcesProviderAccumulating(
        tree=tree, source_map=resources.sources.as_mapping()
    )

    source_provider.updates.subscribe(print_update)

    tree_producer = VfsTreeProducer(resources=resources.set_sources(source_provider))

    await tree_producer.produce(tree, cfg_dict.root.content)

    dir_content = await tree.get_dir_content()
    # pprint(await vfs.dir_content_to_tree(dir_content))

    await source_tmtc.set_messages(Set(messages))
    pprint(await vfs.dir_content_to_tree(dir_content))

    await source_tmtc.set_messages(Set())
    pprint(await vfs.dir_content_to_tree(dir_content))


@pytest.mark.asyncio
async def test_vfs_tree_zip(config_from_file):
    print()

    zip_message1 = msg(username="user2", file=DummyFile("some_archive.zip"))

    cfg_dict = Config.from_yaml(config_from_file)

    builder = DummyTgmountBuilder()
    client = await builder.create_client(cfg_dict)
    resources = await builder.create_resources(client, cfg_dict)

    source_mymount = builder.get_source("my-mount")
    source_tmtc = builder.get_source("tmtc")

    await source_tmtc.set_messages({messages[4], messages[5], zip_message1})

    tree = VfsTree()

    source_provider = SourcesProviderAccumulating(
        tree=tree, source_map=resources.sources.as_mapping()
    )

    tree_producer = VfsTreeProducer(resources=resources.set_sources(source_provider))

    await tree_producer.produce(tree, cfg_dict.root.content)
    dir_content = await tree.get_dir_content()

    pprint(await vfs.dir_content_to_tree(dir_content))


@pytest.mark.asyncio
async def test_vfs_tree_huge(config_from_file):
    print()

    print("generating messages")
    users = [f"user{idx}" for idx in range(0, 100)]
    messages = [msg(text="aaa", username=u) for u in users for idx in range(0, 1000)]

    cfg_dict = Config.from_yaml(config_from_file)

    builder = DummyTgmountBuilder()
    client = await builder.create_client(cfg_dict)
    resources = await builder.create_resources(client, cfg_dict)

    source_mymount = builder.get_source("my-mount")
    source_tmtc = builder.get_source("tmtc")

    await source_tmtc.set_messages(Set(messages))

    tree = VfsTree()

    source_provider = SourcesProviderAccumulating(
        tree=tree, source_map=resources.sources.as_mapping()
    )

    tree_producer = VfsTreeProducer(resources=resources.set_sources(source_provider))
    print("generating tree")

    await tree_producer.produce(tree, cfg_dict.root.content)

    print("generating dir content")
    dir_content = await tree.get_dir_content()

    pprint(await vfs.dir_content_to_tree(dir_content))
