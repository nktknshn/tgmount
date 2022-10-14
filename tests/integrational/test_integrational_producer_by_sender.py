import logging
import aiofiles

import pytest
import tgmount
from tests.helpers.mocked.mocked_storage import StorageEntity
from tests.integrational.helpers import create_config, mdict
from tgmount.tglog import init_logging
from tgmount.tgmount.producers.producer_by_sender import VfsTreeDirBySender
from .fixtures import mnt_dir, files, FixtureFiles, Context
from ..helpers.mocked.mocked_message import MockedSender
import pytest_asyncio
from tgmount.tgclient.guards import MessageWithDocument, MessageWithVideo

BY_SENDER_STRUCTURE = {
    "all": {"producer": "PlainDir"},
    "texts": {"filter": "MessageWithText"},
    "docs": {"filter": "MessageWithDocument"},
    "video": {"filter": "MessageWithVideo"},
}


class _Context(Context):
    expected_dirs: dict
    senders: dict[str, list]


@pytest.fixture
def ctx(mnt_dir: str, caplog):
    return _Context(mnt_dir, caplog=caplog)


@pytest.fixture
def source1(ctx):
    return ctx.storage.get_entity("source1")


SENDERS = 5
MESSAGES = 10
MESSAGES_WITH_DOCS = 3


@pytest_asyncio.fixture
async def prepared_ctx(
    ctx: _Context,
    source1: StorageEntity,
    files: FixtureFiles,
):

    config = create_config(
        message_sources={"source1": "source1", "source2": "source2"},
        root={
            "source": {"source": "source1", "recursive": True},
            "producer": {"BySender": {"dir_structure": BY_SENDER_STRUCTURE}},
        },
    )

    senders = {f"sender_{idx}": [] for idx in range(0, SENDERS)}
    expected_dirs = {}

    for sender_name, messages in senders.items():
        sender = MockedSender(sender_name, None)

        expected_dirs[sender_name] = VfsTreeDirBySender.sanitize(
            f"{sender.id}_{sender_name}"
        )

        for msg_idx in range(0, MESSAGES):
            msg = await source1.message(
                text=f"Message number {msg_idx} from {sender_name}", sender=sender
            )
            messages.append(msg)

        for msg_idx in range(0, MESSAGES_WITH_DOCS):
            msg = await source1.document(
                text=f"Message with Hummingbird number {msg_idx} from {sender_name}",
                sender=sender,
                file=files.Hummingbird,
            )
            messages.append(msg)

            msg = await source1.document(
                # text=f"Message with music number {msg_idx} from {sender_name}",
                sender=sender,
                file=files.music0,
            )
            messages.append(msg)

            msg = await source1.document(
                text=f"Message with zip number {msg_idx} from {sender_name}",
                sender=sender,
                file=files.zip_debrecen,
            )
            messages.append(msg)

    ctx.set_config(config)
    ctx.expected_dirs = expected_dirs
    ctx.senders = senders

    return ctx


@pytest.mark.asyncio
async def test_producer_by_sender_1(
    prepared_ctx: _Context,
    source1: StorageEntity,
    files: FixtureFiles,
):
    expected_dirs = prepared_ctx.expected_dirs
    senders = prepared_ctx.senders

    async def test():
        assert await prepared_ctx.listdir_set("/") == set(expected_dirs.values())

        for dir_name in expected_dirs.values():
            assert await prepared_ctx.listdir_set(dir_name) == {
                "all",
                "texts",
                "docs",
                "video",
            }
            assert (
                await prepared_ctx.listdir_len(dir_name, "all")
                == MESSAGES + MESSAGES_WITH_DOCS * 3
            )
            assert (
                await prepared_ctx.listdir_len(dir_name, "texts")
                == MESSAGES + MESSAGES_WITH_DOCS * 2
            )
            assert (
                await prepared_ctx.listdir_len(dir_name, "docs")
                == MESSAGES_WITH_DOCS * 3
            )
            assert await prepared_ctx.listdir_len(dir_name, "video") == 0

    # prepared_ctx.debug = True
    await prepared_ctx.run_test(test)


import tgmount

# tgmount.fs.exception_handler.catch = False


@pytest.mark.asyncio
async def test_producer_by_sender_update(
    prepared_ctx: _Context,
    source1: StorageEntity,
    files: FixtureFiles,
):
    """Tests updates of the tree"""
    expected_dirs = prepared_ctx.expected_dirs
    senders = prepared_ctx.senders

    # tgmount.fs.FileSystemOperations.logger.setLevel(logging.DEBUG)
    # init_logging(True)
    # prepared_ctx.debug = True

    async def test_update():
        _iter = iter(senders.keys())
        sender = next(_iter)
        sender2 = next(_iter)

        msg = await prepared_ctx.client.sender(sender).send_file(
            source1.entity_id, file=files.video0
        )
        assert MessageWithVideo.guard(msg)
        assert await prepared_ctx.listdir_len(expected_dirs[sender], "video") == 1

        await prepared_ctx.client.delete_messages(source1.entity_id, msg_ids=[msg.id])

        assert await prepared_ctx.listdir_len(expected_dirs[sender], "video") == 0

        for m in senders[sender]:
            await prepared_ctx.client.delete_messages(source1.entity_id, msg_ids=[m.id])

        assert await prepared_ctx.listdir_set("/") == set(expected_dirs.values()) - {
            expected_dirs[sender]
        }

        # for m in senders[sender]:
        await prepared_ctx.client.delete_messages(
            source1.entity_id, msg_ids=[m.id for m in senders[sender2]]
        )

        assert await prepared_ctx.listdir_set("/") == set(expected_dirs.values()) - {
            expected_dirs[sender]
        } - {expected_dirs[sender2]}

    await prepared_ctx.run_test(test_update)
