import logging
from typing import Any, Coroutine

import aiofiles
import pytest
import pytest_asyncio
from tests.integrational.integrational_helpers import ORGRANIZED2
import tgmount
from tests.helpers.mocked.mocked_storage import StorageEntity
from tests.integrational.helpers import (
    async_walkdir,
    create_config,
    mdict,
    concurrently,
)
from tgmount.tgclient.guards import MessageWithDocument, MessageWithVideo
from tgmount.tglog import init_logging
from tgmount.util import Timer, none_fallback
from tgmount.util.col import get_first_key

from .fixtures import Context, FixtureFiles, files, mnt_dir
from .fixtures import Fixtures, fixtures, _Context

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
    # tgmount.fs.FileSystemOperations.logger.setLevel(logging.DEBUG)
    ctx.debug = logging.INFO

    logging.root.setLevel(logging.INFO)

    async def test_update():
        _iter = iter(senders.keys())
        sender = next(_iter)
        sender_dir = expected_dirs[sender]
        sender2 = next(_iter)
        timer = Timer()

        # async for path, subdirs, subfiles in prepared_ctx.walkdir("/"):
        #     pass

        timer.start("message 1", log=True)

        msg1, msg2 = await concurrently(
            ctx.client.sender(sender).send_file(
                source1.entity_id, caption="message 1", file=files.video0
            ),
            ctx.client.sender(sender).send_file(
                source2.entity_id, caption="message 2", file=files.video1
            ),
        )

        assert (
            await ctx.listdir_len(
                str(source1.entity_id), "by-sender", sender_dir, "messages"
            )
            == 12
        )

        timer.print()

    await ctx.run_test(test_update)


# @pytest.mark.asyncio
# async def test_message_while_producing(
#     fixtures: Fixtures,
# ):
#     ctx = _Context.from_fixtures(fixtures)
#     ctx.debug = logging.DEBUG

#     config = create_config(
#         message_sources={"source1": "source1", "source2": "source2"},
#         root={
#             "source": {"source": "source1", "recursive": True},
#             "source1": ORGRANIZED2,
#         },
#     )

#     ctx.set_config(config)

#     ctx.create_senders(10)

#     await ctx.send_text_messages(10)

#     tgm = await ctx.create_tgmount()

#     sender = get_first_key(ctx.senders)
#     sender2 = get_first_key(ctx.senders, 1)

#     sender_dir = ctx.expected_dirs[sender]

#     assert sender
#     assert sender2
#     await tgm.create_fs()

#     await concurrently(
#         ctx.client.sender(sender2).send_file(
#             ctx.source1.entity_id, caption="message 1", file=fixtures.files.video0
#         ),
#         ctx.client.sender(sender).send_file(
#             ctx.source1.entity_id, caption="message 1", file=fixtures.files.video1
#         ),
#     )

#     items = await tgm.vfs_tree.get_dir_content_items(
#         f"/source1/by-sender/{sender_dir}/messages"
#     )

#     print()
#     for item in sorted(items, key=lambda x: x.name):
#         print(item.name)

#     # assert await ctx.listdir_len(sender_dir, "texts") == 11


# import time
