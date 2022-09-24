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

from tests.helpers.dummy_classes import *
from tgmount.tgmount.vfs_structure_producer3 import *
from tgmount import tglog, main
import time

# source = DummyMessageSource()
# files_source = DummyFileSource()

# factory = FileFactoryDefault(files_source)
from pprint import pprint

msg = DummyMessage


def config_from_file():
    with open("tests/config/config.yaml", "r+") as f:
        return f.read()


# class SourcesProviderMessageSourceSupported(SourcesProviderMessageSource):
#     def __init__(
#         self,
#         factory: "FileFactoryDefault",
#         tree: VfsTree,
#         source: tgclient.MessageSourceSubscribableProto,
#     ) -> None:
#         super().__init__(tree, source)
#         self._factory = factory
#         self._filtered_messages = None

#     async def set_messages(self, messages):
#         self._filtered_messages = self._factory.filter_supported(messages)
#         await super().on_update(self, self, self._filtered_messages)

#     async def get_messages(self) -> MessagesSet:

#         if self._filtered_messages is None:
#             messages = await super().get_messages()
#             self._filtered_messages = self._factory.filter_supported(messages)

#         return self._filtered_messages

#     async def on_update(self, source, messages):

#         return await super().on_update(source, messages)


# def get_provider(factory):
#     class SourcesProviderAccumulatingSupported(SourcesProviderAccumulating):
#         MessageSource = (
#             lambda self, tree, source: SourcesProviderMessageSourceSupported(
#                 factory, tree, source
#             )
#         )

#     return SourcesProviderAccumulatingSupported


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

    tree_producer = VfsTreeProducer(resources=resources.set_sources(source_provider))

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
