import logging

import pytest
import pytest_asyncio

import tgmount
from tests.integrational.context import Context
from tests.integrational.integrational_configs import create_config
from tgmount.tgclient.guards import MessageWithVideo
from tgmount.util.timer import Timer

from .fixtures import *

SENDERS = 5
MESSAGES = 10
MESSAGES_WITH_DOCS = 3

BY_SENDER_STRUCTURE = {
    "all": {"producer": "PlainDir"},
    "texts": {"filter": "MessageWithText"},
    "docs": {"filter": "MessageWithDocument"},
    "video": {"filter": "MessageWithVideo"},
}


@pytest_asyncio.fixture
async def ctx(
    fixtures: Fixtures,
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

    ctx = Context.from_fixtures(fixtures)

    ctx.create_senders(SENDERS)
    await ctx.send_text_messages(MESSAGES)
    await ctx.send_docs(MESSAGES_WITH_DOCS)

    ctx.set_config(config)

    return ctx


@pytest.mark.asyncio
async def test_producer_by_sender_1(
    ctx: Context,
):
    expected_dirs = ctx.expected_dirs

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


@pytest.mark.asyncio
async def test_producer_by_sender_update(
    ctx: Context,
    files: FixtureFiles,
):
    """Tests updates of the tree"""
    expected_dirs = ctx.expected_dirs
    senders = ctx.senders
    source1 = ctx.source1

    tgmount.fs.FileSystemOperations.logger.setLevel(logging.INFO)
    # prepared_ctx.debug = logging.DEBUG
    ctx.debug = logging.DEBUG
    # logging.root.setLevel(logging.DEBUG)

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


# @pytest.mark.asyncio
# async def test_producer_by_sender_performance(
#     fixtures: Fixtures,
# ):
#     """Tests updates of the tree"""
#     ctx = Context.from_fixtures(fixtures)

#     config = create_config(
#         message_sources={"source1": "source1", "source2": "source2"},
#         root={
#             "source1": ORGRANIZED2,
#         },
#     )

#     ctx.set_config(config)

#     ctx.create_senders(100)

#     await ctx.send_text_messages(30)
#     await ctx.send_docs(30)

#     expected_dirs = ctx.expected_dirs
#     senders = ctx.senders
#     source1 = ctx.source1
#     files = fixtures.files

#     # tgmount.fs.logger.setLevel(logging.DEBUG)
#     # ctx.debug = logging.DEBUG

#     async def test_update():
#         _iter = iter(senders.keys())
#         sender = next(_iter)
#         sender2 = next(_iter)
#         timer = Timer()

#         # async for path, subdirs, subfiles in prepared_ctx.walkdir("/"):
#         #     pass

#         timer.start("message 1", log=True)

#         msg = await ctx.client.sender(sender).send_file(
#             source1.entity_id, file=files.video0
#         )

#         timer.print()

#     await ctx.run_test(test_update)


import time
