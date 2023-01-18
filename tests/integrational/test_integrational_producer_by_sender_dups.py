import logging

import pytest

from tests.integrational.helpers import concurrently, create_config
from tests.integrational.integrational_helpers import ORGRANIZED2
from tgmount.util.timer import Timer
from tgmount.fs import FileSystemOperations
from .fixtures import (
    Context,
    FixtureFiles,
    Fixtures,
    _Context,
    files,
    fixtures,
    mnt_dir,
)

import tgmount

BY_SENDER_STRUCTURE = {
    "all": {"producer": "PlainDir"},
    "texts": {"filter": "MessageWithText"},
    "docs": {"filter": "MessageWithDocument"},
    "video": {"filter": "MessageWithVideo"},
}


SENDERS = 5
MESSAGES = 10
MESSAGES_WITH_DOCS = 3


@pytest.mark.asyncio
async def test_producer_by_sender_update_dups(
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

    ctx.create_senders(3)

    await ctx.send_text_messages(10)
    # await ctx.send_docs(10)

    expected_dirs = ctx.expected_dirs

    senders = ctx.senders

    source1 = ctx.source1
    source2 = ctx.source2

    files = fixtures.files

    print(expected_dirs)

    tgmount.fs.logger.setLevel(logging.INFO)
    tgmount.tgmount.filters.logger.setLevel(logging.INFO)

    ctx.debug = logging.DEBUG

    # logging.root.setLevel(logging.INFO)

    async def test_update():
        _iter = iter(senders.keys())
        sender1 = next(_iter)

        sender_dir = expected_dirs[sender1]
        sender2 = next(_iter)

        timer = Timer()

        timer.start("message 1")

        msg1, msg2 = await concurrently(
            ctx.client.sender(sender1).send_file(
                source1.entity_id, caption="message 1", file=files.video0
            ),
            ctx.client.sender(sender1).send_file(
                source2.entity_id, caption="message 2", file=files.video1
            ),
        )

        print(msg1)
        print(msg2)

        assert (
            await ctx.listdir_len(
                str(source1.entity_id), "by-sender", sender_dir, "messages"
            )
            == 11
        )

        timer.print()

    await ctx.run_test(test_update)
