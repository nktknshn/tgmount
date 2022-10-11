import os
import random
import time

# factory = FileFactoryDefault(files_source)
from pprint import pprint
from typing import Any, Callable, Optional, TypedDict

from tests.helpers.dummy_classes import *
from tgmount import main, tglog, vfs
from tgmount.config.types import Config
from tgmount.tgclient.message_source import (
    MessageSourceSubscribable,
    Subscribable,
    TelegramMessageSource,
    MessageSourceSimple,
)
from tgmount.tgmount.builder import TgmountBuilder
from tgmount.tgmount.builderbase import TgmountBuilderBase
from tgmount.tgmount.error import TgmountError
from tgmount.tgmount.tgmount_types import TgmountResources
from tgmount.tgmount.types import Set
from tgmount.tgmount.vfs_tree import VfsTree, VfsTreeDir
from tgmount.tgmount.vfs_tree_message_source import SourcesProviderAccumulating
from tgmount.tgmount.vfs_tree_producer import VfsTreeProducer

# source = DummyMessageSource()
# files_source = DummyFileSource()


msg = DummyMessage


def config_from_file():
    with open("tests/config/config.yaml", "r+") as f:
        return f.read()


async def test_vfs_tree_huge():
    print()

    print("generating messages")
    users = [f"user{idx}" for idx in range(0, 50)]
    messages = [
        # 1,
        *[msg(text="aaa", username=u) for u in users for idx in range(0, 1000)],
    ]

    print(len(messages))

    cfg_dict = Config.from_yaml(config_from_file())

    builder = DummyTgmountBuilder()
    client = await builder.create_client(cfg_dict)
    resources = await builder.create_resources(client, cfg_dict)

    source_mymount = builder.get_source("my-mount")
    source_tmtc = builder.get_source("tmtc")

    await source_tmtc.set_messages(Set(messages[0:-1]))
    await source_mymount.set_messages(Set())

    tree = VfsTree()

    source_provider = SourcesProviderAccumulating(
        tree=tree, source_map=resources.sources.as_mapping()
    )

    tree_producer = VfsTreeProducer(
        resources=resources.set_sources(source_provider),
    )

    print("generating tree")
    time1 = time.time_ns()
    await tree_producer.produce(tree, cfg_dict.root.content)

    print("updating")
    time2 = time.time_ns()
    await source_tmtc.add_messages([messages[-1]])

    time3 = time.time_ns()

    print(
        f"done. generating: {int((time2-time1)/1000/1000)} ms. updating: {int((time3-time2)/1000/1000)} ms."
    )

    # dir_content = await tree.get_dir_content()
    # pprint(await vfs.dir_content_to_tree(dir_content))


if __name__ == "__main__":
    main.util.run_main(test_vfs_tree_huge, forever=False)
