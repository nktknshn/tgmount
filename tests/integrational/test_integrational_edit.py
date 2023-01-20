import logging
import pytest

import tgmount
from tests.helpers.asyncio import read_bytes
from tests.helpers.mocked.mocked_storage import StorageEntity
from tests.integrational.helpers import mdict
from tests.integrational.integrational_configs import create_config
from tests.integrational.integrational_test import TgmountIntegrationContext
from tests.integrational.context import Context
from tgmount.fs.operations import FileSystemOperations
from tgmount.fs.update import FileSystemOperationsUpdate
from tgmount.tgmount.vfs_tree import VfsTree, VfsTreeDir

from .fixtures import *


@pytest.mark.asyncio
async def test_simple1(fixtures: Fixtures):
    ctx = Context.from_fixtures(fixtures)
    config = create_config(
        message_sources={"source1": "source1"}, root={"source": "source1"}
    )
    ctx.set_config(config)
    # ctx.debug = logging.DEBUG

    async def test():
        msg1 = await ctx.source1.message("text message 1")
        assert await ctx.listdir("/") == ["1_message.txt"]
        msg1_copy = msg1.clone()
        msg1_copy.text = "edit"
        await ctx.client.edit_message(msg1, msg1_copy)
        assert await ctx.read_text("1_message.txt") == "edit"

    await ctx.run_test(test)


FileSystemOperations.logger.setLevel(logging.CRITICAL)
VfsTree.logger.setLevel(logging.CRITICAL)
VfsTreeDir.logger.setLevel(logging.CRITICAL)


@pytest.mark.asyncio
async def test_update_document(fixtures: Fixtures):
    ctx = Context.from_fixtures(fixtures)
    config = create_config(
        message_sources={"source1": "source1"},
        root={
            "source": {"source": "source1", "recursive": True},
            "all": {"filter": "All"},
            "docs": {"filter": "MessageWithDocument"},
            "music": {"filter": "MessageWithMusic"},
            "image": {"filter": "MessageWithDocumentImage"},
            "texts": {"filter": "MessageWithText", "treat_as": "MessageWithText"},
        },
    )
    ctx.set_config(config)
    ctx.debug = logging.ERROR

    async def test():
        msg1 = await ctx.source1.document(file=ctx.files.music0, audio=True)
        assert await ctx.listdir("/docs") == ["1_kareem.mp3"]
        assert await ctx.listdir("/music") == ["1_kareem.mp3"]
        assert await ctx.listdir("/texts") == []

        msg1_copy = msg1.clone()
        msg1_copy.text = "edit"

        msg2 = await ctx.client.edit_message(msg1, msg1_copy)

        assert await ctx.listdir("/docs") == ["1_kareem.mp3"]
        assert await ctx.listdir("/texts") == ["1_message.txt"]

        msg2_copy = msg2.clone()
        msg2_copy.text = None

        msg3 = await ctx.client.edit_message(msg2, msg2_copy)

        assert await ctx.listdir("/docs") == ["1_kareem.mp3"]
        assert await ctx.listdir("/texts") == []

        msg4 = await ctx.source1.document(
            file=ctx.files.Hummingbird, text="more text", put=False, image=True
        )

        msg4.id = msg3.id

        await ctx.client.edit_message(msg3, msg4)

        assert await ctx.listdir("/docs") == ["1_Hummingbird.jpg"]
        assert await ctx.listdir("/texts") == ["1_message.txt"]
        assert await ctx.listdir("/music") == []
        assert await ctx.listdir("/image") == ["1_Hummingbird.jpg"]

    await ctx.run_test(test)
