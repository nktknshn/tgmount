import logging
from typing import Any

import aiofiles
import pytest
import pytest_asyncio
from tests.integrational.integrational_helpers import ORGRANIZED2
import tgmount
from tests.helpers.mocked.mocked_storage import StorageEntity
from tests.integrational.helpers import async_walkdir, create_config, mdict
from tgmount.tgclient.guards import MessageWithDocument, MessageWithVideo
from tgmount.tglog import init_logging
from tgmount.tgmount.producers.producer_by_sender import VfsTreeDirBySender
from tgmount.util import Timer

from ..helpers.mocked.mocked_message import MockedSender
from .fixtures import Context, FixtureFiles, files, mnt_dir

BY_SENDER_STRUCTURE = {
    "all": {"producer": "PlainDir"},
    "texts": {"filter": "MessageWithText"},
    "docs": {"filter": "MessageWithDocument"},
    "video": {"filter": "MessageWithVideo"},
}


@pytest.fixture
def empty_ctx(mnt_dir: str, caplog, files: FixtureFiles):
    ctx = _Context(mnt_dir, caplog=caplog)
    ctx.files = files
    ctx.init()
    return ctx


@pytest.fixture
def fixtures(mnt_dir: str, caplog, files: FixtureFiles):
    f = Fixtures()
    f.files = files
    f.caplog = caplog
    f.mnt_dir = mnt_dir
    return f


SENDERS = 5
MESSAGES = 10
MESSAGES_WITH_DOCS = 3


class Fixtures:
    files: FixtureFiles
    mnt_dir: str
    caplog: Any


class _Context(Context):
    expected_dirs: dict
    senders: dict[str, list]
    source1: StorageEntity
    files: FixtureFiles

    @staticmethod
    def from_fixtures(fixtures: Fixtures):
        ctx = _Context(fixtures.mnt_dir, caplog=fixtures.caplog)
        ctx.files = fixtures.files
        ctx.init()
        return ctx

    def init(self):
        self.source1 = self.storage.get_entity("source1")

    def create_senders(self, count: int):
        self.expected_dirs = {}
        self.senders = {f"sender_{idx}": [] for idx in range(0, count)}

        for sender_name, messages in self.senders.items():
            sender = MockedSender(sender_name, None)
            self.expected_dirs[sender_name] = VfsTreeDirBySender.sanitize(
                f"{sender.id}_{sender_name}"
            )

    async def send_text_messages(self, count: int):
        for sender_name, messages in self.senders.items():
            sender = MockedSender(sender_name, None)
            for msg_idx in range(0, count):
                msg = await self.source1.message(
                    text=f"Message number {msg_idx} from {sender_name}", sender=sender
                )
                messages.append(msg)

    async def send_docs(self, count: int):
        files = self.files
        for sender_name, messages in self.senders.items():
            sender = MockedSender(sender_name, None)
            for msg_idx in range(0, MESSAGES_WITH_DOCS):
                msg = await self.source1.document(
                    text=f"Message with Hummingbird number {msg_idx} from {sender_name}",
                    sender=sender,
                    file=files.Hummingbird,
                )
                messages.append(msg)

                msg = await self.source1.document(
                    # text=f"Message with music number {msg_idx} from {sender_name}",
                    sender=sender,
                    file=files.music0,
                )
                messages.append(msg)

                msg = await self.source1.document(
                    text=f"Message with zip number {msg_idx} from {sender_name}",
                    sender=sender,
                    file=files.zip_debrecen,
                )
                messages.append(msg)


@pytest_asyncio.fixture
async def ctx(
    empty_ctx: _Context,
    files: FixtureFiles,
):
    config = create_config(
        message_sources={"source1": "source1", "source2": "source2"},
        root={
            "source": {"source": "source1", "recursive": True},
            "producer": {
                "BySender": {
                    "dir_structure": BY_SENDER_STRUCTURE,
                    "use_get_sender": True,
                }
            },
        },
    )

    empty_ctx.create_senders(SENDERS)
    await empty_ctx.send_text_messages(MESSAGES)
    await empty_ctx.send_docs(MESSAGES_WITH_DOCS)

    empty_ctx.set_config(config)

    return empty_ctx


@pytest.mark.asyncio
async def test_producer_by_sender_1(
    ctx: _Context,
):
    expected_dirs = ctx.expected_dirs
    # senders = prepared_ctx.senders
    # prepared_ctx.debug = True

    async def test():
        assert await ctx.listdir_set("/") == set(expected_dirs.values())

        for dir_name in expected_dirs.values():
            assert await ctx.listdir_set(dir_name) == {
                "all",
                "texts",
                "docs",
                "video",
            }
            assert (
                await ctx.listdir_len(dir_name, "all")
                == MESSAGES + MESSAGES_WITH_DOCS * 3
            )
            assert (
                await ctx.listdir_len(dir_name, "texts")
                == MESSAGES + MESSAGES_WITH_DOCS * 2
            )
            assert await ctx.listdir_len(dir_name, "docs") == MESSAGES_WITH_DOCS * 3
            assert await ctx.listdir_len(dir_name, "video") == 0

    await ctx.run_test(test)


import tgmount


# tgmount.fs.exception_handler.catch = False
@pytest_asyncio.fixture
async def perfomance_ctx(
    empty_ctx: _Context,
    files: FixtureFiles,
):
    config = create_config(
        message_sources={"source1": "source1", "source2": "source2"},
        root={
            "source": {"source": "source1", "recursive": True},
            "producer": {"BySender": {"dir_structure": BY_SENDER_STRUCTURE}},
        },
    )

    empty_ctx.create_senders(SENDERS)
    await empty_ctx.send_text_messages(MESSAGES)
    await empty_ctx.send_docs(MESSAGES_WITH_DOCS)

    empty_ctx.set_config(config)

    return empty_ctx


@pytest.mark.asyncio
async def test_producer_by_sender_update(
    ctx: _Context,
    files: FixtureFiles,
):
    """Tests updates of the tree"""
    expected_dirs = ctx.expected_dirs
    senders = ctx.senders
    source1 = ctx.source1

    tgmount.fs.FileSystemOperations.logger.setLevel(logging.INFO)
    # prepared_ctx.debug = logging.DEBUG
    ctx.debug = logging.DEBUG
    logging.root.setLevel(logging.DEBUG)

    async def test_update():
        _iter = iter(senders.keys())
        sender = next(_iter)
        sender2 = next(_iter)

        # async for path, subdirs, subfiles in prepared_ctx.walkdir("/"):
        #     pass

        msg = await ctx.client.sender(sender).send_file(
            source1.entity_id, file=files.video0
        )
        assert MessageWithVideo.guard(msg)

        # producer should add video message
        assert await ctx.listdir_len(expected_dirs[sender], "video") == 1

        await ctx.client.delete_messages(source1.entity_id, msg_ids=[msg.id])

        # producer should add remove message
        assert await ctx.listdir_len(expected_dirs[sender], "video") == 0

        # producer should remove sender's folder if there is no messages left
        for m in senders[sender]:
            await ctx.client.delete_messages(source1.entity_id, msg_ids=[m.id])

        assert await ctx.listdir_set("/") == set(expected_dirs.values()) - {
            expected_dirs[sender]
        }

        # producer should remove sender's folder if there is no messages left
        await ctx.client.delete_messages(
            source1.entity_id, msg_ids=[m.id for m in senders[sender2]]
        )

        assert await ctx.listdir_set("/") == set(expected_dirs.values()) - {
            expected_dirs[sender]
        } - {expected_dirs[sender2]}

    await ctx.run_test(test_update)


@pytest.mark.asyncio
async def test_producer_by_sender_performance(
    fixtures: Fixtures,
):
    """Tests updates of the tree"""
    ctx = _Context.from_fixtures(fixtures)

    config = create_config(
        message_sources={"source1": "source1", "source2": "source2"},
        root={
            "source1": ORGRANIZED2,
        },
    )

    ctx.set_config(config)

    ctx.create_senders(100)

    await ctx.send_text_messages(30)
    await ctx.send_docs(30)

    expected_dirs = ctx.expected_dirs
    senders = ctx.senders
    source1 = ctx.source1
    files = fixtures.files

    # tgmount.fs.FileSystemOperations.logger.setLevel(logging.DEBUG)
    ctx.debug = logging.INFO

    logging.root.setLevel(logging.INFO)

    async def test_update():
        _iter = iter(senders.keys())
        sender = next(_iter)
        sender2 = next(_iter)
        timer = Timer()

        # async for path, subdirs, subfiles in prepared_ctx.walkdir("/"):
        #     pass

        timer.start("message 1", log=True)

        msg = await ctx.client.sender(sender).send_file(
            source1.entity_id, file=files.video0
        )

        timer.print()

    await ctx.run_test(test_update)


import time
