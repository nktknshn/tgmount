import asyncio
import logging
import threading
from typing import TypedDict

import pytest

import tgmount.config as config
from tests.integrational.integrational_configs import create_config
from tgmount import tglog
from tgmount.tgmount.tgmount_builder import TgmountBuilder

from ..helpers.spawn import spawn_fs_ops
from .fixtures import *
from ..helpers.fixtures_tgclient import tgclient_second
from .helpers import async_listdir

TESTING_CHANNEL = "tgmounttestingchannel"

Props = TypedDict(
    "Props",
    debug=int,
    ev0=threading.Event,
    ev1=threading.Event,
    cfg=config.Config,
)


class MyTgmountBuilder(TgmountBuilder):
    def __init__(self, client_kwargs={}) -> None:
        super().__init__()
        self._client_kwargs = client_kwargs

    async def create_client(self, cfg: config.Config):
        return await super().create_client(cfg, **self._client_kwargs)


async def main_test1(props: Props, on_event):

    # on_event(props["ev0"], print_tasks)
    # on_event(props["ev1"], print_tasks)

    async def on_new_message(event):
        print(event)

    tglog.init_logging(props["debug"])

    test_logger = tglog.getLogger("main_test1")

    # tglog.getLogger("FileSystemOperations()").setLevel(logging.ERROR)
    # logging.getLogger("telethon").setLevel(logging.INFO)

    test_logger.debug("Building...")
    builder = MyTgmountBuilder(
        client_kwargs=dict(
            # sequential_updates=True,
        )
    )

    test_logger.debug("Creating...")
    tgm = await builder.create_tgmount(props["cfg"])

    # tgm.client.add_event_handler(
    #     on_new_message, events.NewMessage(chats=TESTING_CHANNEL)
    # )

    test_logger.debug("Auth...")
    await tgm.client.auth()

    # tgm.client.on(events.NewMessage(chats=TESTING_CHANNEL))(on_new_message)

    await tgm.fetch_messages()

    test_logger.debug("Creating FS...")

    await tgm.create_fs()
    await tgm.events_dispatcher.resume()

    test_logger.debug("Returng FS")

    return tgm.fs


from telethon import TelegramClient


@pytest.mark.asyncio
async def test_fs_tg_test1(
    mnt_dir, caplog, tgclient_second: TelegramClient, files: FixtureFiles
):

    client = tgclient_second
    # caplog.set_level(logging.DEBUG)
    helper = TgmountIntegrationContext(mnt_dir, caplog=caplog)
    # helper.debug = logging.DEBUG

    for ctx in spawn_fs_ops(
        main_test1,
        props=lambda ctx: {
            "debug": logging.DEBUG,
            "ev0": ctx.mgr.Event(),
            "ev1": ctx.mgr.Event(),
            "cfg": create_config(
                message_sources={
                    "tmtc": TESTING_CHANNEL,
                },
                root={
                    "tmtc": {
                        "source": {"source": "tmtc", "recursive": True},
                        "all": {"filter": "All"},
                        # "wrappers": "ExcludeEmptyDirs",
                        "texts": {"filter": "MessageWithText"},
                        "images": {"filter": "MessageWithDocumentImage"},
                    },
                },
            ),
        },
        mnt_dir=mnt_dir,
        min_tasks=10,
    ):

        # subfiles = await async_listdir(ctx.path("tmtc/all/"))
        # len1 = len(subfiles)
        # # await print_tasks()
        # # ctx.props["ev0"].set()
        # # print("Sending message 1")

        # msg0 = await client.send_message(TESTING_CHANNEL, message="asdsad")

        # # print(f"Done Sending message 1: {msg0.id}")

        # assert len1 > 0
        # # print("Sending message 2")

        # msg1 = await client.send_message(
        #     TESTING_CHANNEL, file="tests/fixtures/small_zip.zip"
        # )
        # # ctx.props["ev1"].set()
        # # print(f"Done Sending message 2: {msg1.id}")
        # msg2 = await client.send_message(
        #     TESTING_CHANNEL, file="tests/fixtures/small_zip.zip"
        # )
        # # print(f"Done Sending message 3: {msg2.id}")
        # await asyncio.sleep(1)
        # subfiles = await async_listdir(ctx.path("tmtc/all/"))

        # assert len(subfiles) == len1 + 3

        # await client.delete_messages(TESTING_CHANNEL, [msg0.id, msg1.id, msg2.id])

        # # print(f"Removed messages")
        # await asyncio.sleep(1)
        # subfiles = await async_listdir(ctx.path("tmtc/all/"))
        # assert len(subfiles) == len1

        msg3 = await client.send_message(TESTING_CHANNEL, message="hello")

        assert (await helper.listdir("tmtc/all/")).count(f"{msg3.id}_message.txt") == 1

        assert await helper.read_text(f"tmtc/all/{msg3.id}_message.txt") == "hello"

        assert (await helper.stat(f"tmtc/all/{msg3.id}_message.txt")).st_size == 5

        msg3 = await client.edit_message(
            TESTING_CHANNEL, message=msg3.id, text="hello hello", file=files.Hummingbird
        )

        assert (await helper.stat(f"tmtc/all/{msg3.id}_message.txt")).st_size == 11

        assert (
            await helper.read_text(f"tmtc/all/{msg3.id}_message.txt") == "hello hello"
        )

        assert (await helper.listdir(ctx.path("tmtc/images/"))).count(
            f"{msg3.id}_Hummingbird.jpg"
        ) == 1

        await client.delete_messages(TESTING_CHANNEL, [msg3.id])
