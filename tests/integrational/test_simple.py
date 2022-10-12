import copy
import logging
import os
from typing import Mapping

import pytest
import tgmount
from tests.helpers.mocked.mocked_storage import StorageEntity
from tests.integrational.helpers import TESTING_CHANNEL, create_config, mdict
from ..helpers.mocked.mocked_message import MockedMessage, MockedSender
from .integrational_helpers import BY_SENDER, DEFAULT_ROOT, UNPACKED
from .integrational_test import (
    TgmountIntegrationContext as Context,
    mnt_dir,
    read_bytes,
)


@pytest.fixture
def ctx(mnt_dir):
    return Context(mnt_dir)


@pytest.fixture
def source1(ctx):
    return ctx.storage.get_entity("source1")


@pytest.fixture
def source2(ctx):
    return ctx.storage.get_entity("source2")


# build_root(DEFAULT_ROOT).enter("source1").update({"all": {"filter": "All"}})

# DEFAULT_ROOT: Mapping = {
#     "source1": {"source": {"source": "source1"}},
# }


@pytest.mark.asyncio
async def test_fails_empty_root(caplog, ctx, source1: StorageEntity):
    async def test():
        pass

    with pytest.raises(tgmount.config.ConfigError):
        await ctx.run_test(test, {})


@pytest.mark.asyncio
async def test_simple1(caplog, ctx, source1: StorageEntity):

    await source1.message(text="hello1")
    await source1.message(text="hello2")
    await source1.message(text="hello3")

    async def test():
        assert await ctx.listdir_set("/") == set({"source1"})
        assert await ctx.listdir_set("/source1") == {
            "1_message.txt",
            "2_message.txt",
            "3_message.txt",
        }

    await ctx.run_test(test, {"source1": {"source": "source1"}})
    await ctx.run_test(test, {"source1": {"source": {"source": "source1"}}})


@pytest.mark.asyncio
async def test_recursive_source_empty(caplog, ctx, source1: StorageEntity):
    root = {"source1": {"source": {"source": "source1", "recursive": True}}}
    await source1.message(text="hello1")

    async def test():
        assert await ctx.listdir_set("/") == set({"source1"})
        assert await ctx.listdir_set("/source1") == set()

    await ctx.run_test(test, root)


# tgmount.tglog.getLogger("TgmountConfigReader()").setLevel(logging.DEBUG)


@pytest.mark.asyncio
async def test_recursive_source_with_filter(caplog, ctx, source1: StorageEntity):
    root = {
        "source1": {
            "source": {"source": "source1", "recursive": True},
            "filter": "All",
        }
    }

    await source1.message(text="hello1")
    await source1.message(text="hello2")
    await source1.message(text="hello3")

    async def test():
        assert await ctx.listdir_set("/") == set({"source1"})
        assert await ctx.listdir_set("/source1") == {
            "1_message.txt",
            "2_message.txt",
            "3_message.txt",
        }

    await ctx.run_test(test, root)


@pytest.mark.asyncio
async def test_filtered(caplog, ctx, source1: StorageEntity):
    root = {
        "source1": {
            "source": {"source": "source1", "recursive": True},
            "filter": "All",
            "text-messages": {"filter": "MessageWithText"},
        }
    }

    root2 = (
        mdict(root)
        .update({"treat_as": "MessageWithText"}, at="/source1/text-messages")
        .get()
    )

    await source1.message(text="hello1")
    await source1.message(text="hello2")
    await source1.message(text="hello3")
    await source1.document_file_message(
        text="hello4", file="tests/fixtures/2010_debrecen.zip"
    )
    await source1.document_file_message(file="tests/fixtures/2010_debrecen.zip")

    async def test_without_treat_as():
        assert await ctx.listdir_set("/") == set({"source1"})
        assert await ctx.listdir_set("/source1") == {
            "1_message.txt",
            "2_message.txt",
            "3_message.txt",
            "4_2010_debrecen.zip",
            "5_2010_debrecen.zip",
            "text-messages",
        }
        assert await ctx.listdir_set("/source1/text-messages") == {
            "1_message.txt",
            "2_message.txt",
            "3_message.txt",
            "4_2010_debrecen.zip",
        }

    async def test_with_treat_as():
        assert await ctx.listdir_set("/") == set({"source1"})
        assert await ctx.listdir_set("/source1") == {
            "1_message.txt",
            "2_message.txt",
            "3_message.txt",
            "4_2010_debrecen.zip",
            "5_2010_debrecen.zip",
            "text-messages",
        }

        assert await ctx.listdir_set("/source1/text-messages") == {
            "1_message.txt",
            "2_message.txt",
            "3_message.txt",
            "4_message.txt",
        }

        assert set(
            [
                await ctx.read_text(f)
                for f in await ctx.listdir_set("/source1/text-messages", full_path=True)
            ]
        ) == {"hello1", "hello2", "hello3", "hello4"}

        assert await ctx.read_bytes("/source1/4_2010_debrecen.zip") == await read_bytes(
            "tests/fixtures/2010_debrecen.zip"
        )

    await ctx.run_test(test_without_treat_as, root)
    await ctx.run_test(test_with_treat_as, root2)


@pytest.mark.asyncio
async def test_two_sources(
    caplog, ctx: Context, source1: StorageEntity, source2: StorageEntity
):
    config = create_config(message_sources={"source1": "source1", "source2": "source2"})

    config1 = config.set_root(
        {
            "source1": {"source": "source1", "filter": "All"},
            "source2": {"source": "source2", "filter": "All"},
        }
    )

    await source1.message(text="hello1")
    await source1.message(text="hello2")

    await source2.message(text="hello source2 1")
    await source2.message(text="hello source2 2")
    await source2.message(text="hello source2 3")

    async def test1():
        assert await ctx.listdir_len("/source1") == 2
        assert await ctx.listdir_len("/source2") == 3

    await ctx.run_test(test1, config1)

    config2 = config.set_root(
        {
            "mixed_sources": {
                "source": "source1",
                "filter": "All",
                "source2": {
                    "source": "source2",
                    "filter": "All",
                },
            },
        }
    )

    async def test2():
        assert await ctx.listdir_set("/mixed_sources") == {
            "1_message.txt",
            "2_message.txt",
            "source2",
        }
        assert await ctx.listdir_set("/mixed_sources/source2") == {
            "1_message.txt",
            "2_message.txt",
            "3_message.txt",
        }

    await ctx.run_test(test2, config2)
