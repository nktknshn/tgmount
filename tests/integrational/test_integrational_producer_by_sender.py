import logging
import aiofiles

import pytest
import tgmount
from tests.helpers.mocked.mocked_storage import StorageEntity
from tests.integrational.helpers import create_config, mdict
from tgmount.tgmount.producers.producer_by_sender import VfsTreeDirBySender
from .fixtures import *
from ..helpers.mocked.mocked_message import MockedSender

BY_SENDER_STRUCTURE = {
    "all": {"producer": "PlainDir"},
    "all-texts": {"filter": "MessageWithText"},
    "all-docs": {"filter": "MessageWithDocument"},
}


@pytest.mark.asyncio
async def test_producer_by_sender_1(
    ctx: Context,
    source1: StorageEntity,
    source2: StorageEntity,
    files: FixtureFiles,
):
    SENDERS = 10
    MESSAGES = 100

    config = create_config(
        message_sources={"source1": "source1", "source2": "source2"},
        root={
            "source": {"source": "source1", "recursive": True},
            "producer": {"BySender": {"dir_structure": BY_SENDER_STRUCTURE}},
        },
    )

    senders = {f"sender_{idx}": [] for idx in range(0, SENDERS)}
    expected_dirs = set()

    for sender_name, messages in senders.items():
        sender = MockedSender(sender_name, None)

        expected_dirs.add(
            VfsTreeDirBySender.sanitize(f"{sender.id}_{sender_name}"),
        )

        for msg_idx in range(0, MESSAGES):
            msg = await source1.message(
                text=f"Message number {msg_idx} from {sender_name}", sender=sender
            )
            messages.append(msg)

    async def test():
        assert await ctx.listdir_set("/") == expected_dirs

        for dir_name in expected_dirs:
            assert await ctx.listdir_set(dir_name) == {"all", "all-texts", "all-docs"}
            assert await ctx.listdir_len(dir_name, "all") == 100
            assert await ctx.listdir_len(dir_name, "all-texts") == 100
            assert await ctx.listdir_len(dir_name, "all-docs") == 0

    # ctx.debug = True
    await ctx.run_test(test, config)
