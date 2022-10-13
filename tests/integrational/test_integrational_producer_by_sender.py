import logging
import aiofiles

import pytest
import tgmount
from tests.helpers.mocked.mocked_storage import StorageEntity
from tests.integrational.helpers import create_config, mdict
from tgmount.tgmount.producers.producer_by_sender import VfsTreeDirBySender
from .fixtures import *
from ..helpers.mocked.mocked_message import MockedSender

from tgmount.tgclient.guards import MessageWithDocument, MessageWithVideo

BY_SENDER_STRUCTURE = {
    "all": {"producer": "PlainDir"},
    "texts": {"filter": "MessageWithText"},
    "docs": {"filter": "MessageWithDocument"},
    "video": {"filter": "MessageWithVideo"},
}


@pytest.mark.asyncio
async def test_producer_by_sender_1(
    ctx: Context,
    source1: StorageEntity,
    source2: StorageEntity,
    files: FixtureFiles,
):
    SENDERS = 5
    MESSAGES = 100
    MESSAGES_WITH_DOCS = 33

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

    async def test():
        assert await ctx.listdir_set("/") == set(expected_dirs.values())

        for dir_name in expected_dirs.values():
            assert await ctx.listdir_set(dir_name) == {"all", "texts", "docs", "video"}
            assert await ctx.listdir_len(dir_name, "all") == 199
            assert await ctx.listdir_len(dir_name, "texts") == 166
            assert await ctx.listdir_len(dir_name, "docs") == 99
            assert await ctx.listdir_len(dir_name, "video") == 0

    async def test_update():
        # assert await ctx.listdir_set("/") == set(expected_dirs.values())
        sender = next(iter(senders.keys()))

        msg = await ctx.client.sender(sender).send_file(
            source1.entity_id, file=files.video0
        )

        assert MessageWithVideo.guard(msg)

        assert await ctx.listdir_len(expected_dirs[sender], "video") == 1

    ctx.debug = True
    await ctx.run_test(test, config)
    await ctx.run_test(test_update, config)
