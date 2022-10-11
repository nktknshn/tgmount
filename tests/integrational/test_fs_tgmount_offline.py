import asyncio
import logging
import os
from typing import Iterable, Mapping, TypedDict

import pyfuse3
import pytest
import pytest_asyncio
import tgmount.config as config
import tgmount.tgclient as tg
from tests.helpers.mocked.mocked_storage import EntityId, MockedTelegramStorage
from tests.helpers.mount import handle_mount
from tgmount import tglog
from tgmount.main.util import mount_ops
from tgmount.tgmount.builder import TgmountBuilder

from ..helpers.fixtures import mnt_dir
from ..helpers.mocked.mocked_client import MockedClientReader, MockedClientWriter
from ..helpers.mocked.mocked_message import MockedFile, MockedMessage, MockedSender
from .helpers import *

# import os


# Message = telethon.tl.custom.Message
# Document = telethon.types.Document


class MockedTgmountBuilderBase(TgmountBuilder):
    # TelegramClient = MockedClientReader

    def __init__(self, storage: MockedTelegramStorage) -> None:
        self._storage = storage

    async def create_client(self, cfg: config.Config, **kwargs):
        return MockedClientReader(self._storage)


async def main_function(
    *, mnt_dir: str, cfg: config.Config, debug: bool, storage: MockedTelegramStorage
):

    tglog.init_logging(debug)
    test_logger = tglog.getLogger("main_test1")

    tglog.getLogger("FileSystemOperations()").setLevel(logging.ERROR)
    logging.getLogger("telethon").setLevel(logging.DEBUG)

    test_logger.debug("Building...")
    builder = MockedTgmountBuilderBase(storage=storage)

    test_logger.debug("Creating...")
    tgm = await builder.create_tgmount(cfg)

    test_logger.debug("Auth...")
    await tgm.client.auth()

    test_logger.debug("Creating FS...")
    await tgm.create_fs()

    test_logger.debug("Returng FS")

    await mount_ops(tgm.fs, mount_dir=mnt_dir, min_tasks=10)


async def run_test(mount_coro, test_coro):
    mount_task = asyncio.create_task(mount_coro)
    test_task = asyncio.create_task(test_coro)

    done, pending = await asyncio.wait(
        [mount_task, test_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    done.pop().result()
    pending.pop().cancel()


async def _run_test(
    test_func,
    *,
    mnt_dir: str,
    cfg: config.Config,
    storage: MockedTelegramStorage,
    debug: bool,
):
    await run_test(
        main_function(mnt_dir=mnt_dir, cfg=cfg, storage=storage, debug=True),
        test_func(),
    )


import copy


UNPACKED = dict(
    filter="MessageWithZip",
    cache="memory1",
    wrappers="ZipsAsDirs",
)
BY_SENDER = dict(filter="All", producer="BySender")


@pytest.mark.asyncio
async def test_itergrational1(mnt_dir, caplog):
    caplog.set_level(logging.DEBUG)

    storage = MockedTelegramStorage()
    tmtc = storage.get_entity(TESTING_CHANNEL)
    cfg = create_config(
        root={
            **DEFAULT_ROOT,
            "tmtc": {
                **(DEFAULT_ROOT["tmtc"]),
                "unpacked": UNPACKED,
                "music": dict(filter="MessageWithMusic"),
            },
        }
    )

    await tmtc.message(message_text="aaaa")
    await tmtc.document_file_message(file="tests/fixtures/2010_debrecen.zip")
    await tmtc.audio_file_message(
        file="tests/fixtures/files/Tvrdý _ Havelka - Žiletky.mp3",
        duration=666,
        performer="behemoth",
        title="Satan",
        file_name="behemoth_satan.mp3",
    )

    mount_task = main_function(
        mnt_dir=mnt_dir,
        cfg=cfg,
        debug=True,
        storage=storage,
    )

    @handle_mount(mnt_dir)
    async def _test():
        client = MockedClientWriter(storage=storage)
        subfiles = await async_listdir(os.path.join(mnt_dir, "tmtc/all/"))
        assert len(subfiles) == 3
        msg1 = await client.send_message(TESTING_CHANNEL, message="lsksksks")
        subfiles = await async_listdir(os.path.join(mnt_dir, "tmtc/all/"))
        assert len(subfiles) == 4
        await client.delete_messages(TESTING_CHANNEL, msg_ids=[msg1.id])
        subfiles = await async_listdir(os.path.join(mnt_dir, "tmtc/all/"))
        assert len(subfiles) == 3
        zips = await async_listdir(
            os.path.join(mnt_dir, "tmtc/unpacked/2_2010_debrecen.zip")
        )
        assert "2010_Debrecen" in zips
        music = await async_listdir(os.path.join(mnt_dir, "tmtc/music"))
        assert len(music) == 1

    await run_test(mount_task, _test())


@pytest.mark.asyncio
async def test_itergrational2(mnt_dir, caplog):
    storage = MockedTelegramStorage()
    tmtc = storage.get_entity(TESTING_CHANNEL)
    client = MockedClientWriter(storage=storage)

    root: dict = copy.deepcopy(dict(DEFAULT_ROOT))
    root["tmtc"].update({"by-sender": BY_SENDER})
    cfg = create_config(root=root)

    senders = [f"sender_{idx}" for idx in range(0, 10)]
    senders_messages: list[list[MockedMessage]] = [[] for _ in senders]

    for sender_id, (sender, messages) in enumerate(zip(senders, senders_messages)):
        for idx in range(0, 10):
            messages.append(
                await tmtc.message(
                    message_text=f"Message from {sender} number {idx}",
                    sender=MockedSender(sender, sender_id),
                )
            )

    @handle_mount(mnt_dir)
    async def _test():
        subfiles = await async_listdir(os.path.join(mnt_dir, "tmtc/by-sender/"))
        assert len(subfiles) == 10

        await client.delete_messages(
            TESTING_CHANNEL, msg_ids=[senders_messages[0][0].id]
        )

        subfiles = await async_listdir(
            os.path.join(
                mnt_dir,
                f"tmtc/by-sender/{senders_messages[0][0].sender.id}_{senders[0]}",
            )
        )
        assert len(subfiles) == 9

        await client.delete_messages(
            TESTING_CHANNEL, msg_ids=[m.id for m in senders_messages[1]]
        )

        subfiles = await async_listdir(os.path.join(mnt_dir, "tmtc/by-sender/"))
        assert len(subfiles) == 9

    await _run_test(_test, mnt_dir=mnt_dir, cfg=cfg, storage=storage, debug=True)
