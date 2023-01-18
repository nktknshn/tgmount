import pytest

import tgmount
from tests.helpers.asyncio import read_bytes
from tests.helpers.mocked.mocked_storage import StorageEntity
from tests.integrational.helpers import mdict
from tests.integrational.integrational_configs import create_config
from tests.integrational.integrational_test import TgmountIntegrationContext

from .fixtures import *


@pytest.mark.asyncio
async def test_fails_empty_root(
    caplog, ctx: TgmountIntegrationContext, source1: StorageEntity
):
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

    await source1.document(text="hello4", file="tests/fixtures/2010_debrecen.zip")
    await source1.document(file="tests/fixtures/2010_debrecen.zip")

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
            await ctx.read_texts(
                await ctx.listdir_set("/source1/text-messages", full_path=True)
            )
        ) == {"hello1", "hello2", "hello3", "hello4"}

        assert await ctx.read_bytes("/source1/4_2010_debrecen.zip") == await read_bytes(
            "tests/fixtures/2010_debrecen.zip"
        )

    await ctx.run_test(test_without_treat_as, root)
    await ctx.run_test(test_with_treat_as, root2)


@pytest.mark.asyncio
async def test_two_sources_1(
    caplog,
    ctx: TgmountIntegrationContext,
    source1: StorageEntity,
    source2: StorageEntity,
):
    """Different sources can be used"""
    config = create_config(
        message_sources={"source1": "source1", "source2": "source2"},
        root={
            "source1": {"source": "source1", "filter": "All"},
            "source2": {"source": "source2", "filter": "All"},
        },
    )

    await source1.text_messages(texts=["hello1", "hello2"])
    await source2.text_messages(
        texts=["hello source2 1", "hello source2 2", "hello source2 3"]
    )

    async def test1():
        assert await ctx.listdir_len("/source1") == 2
        assert await ctx.listdir_len("/source2") == 3

    await ctx.run_test(test1, config)


@pytest.mark.asyncio
async def test_two_sources_2(
    ctx: TgmountIntegrationContext,
    source1: StorageEntity,
    source2: StorageEntity,
):
    """Different sources can be used inside a structure"""
    config = create_config(
        message_sources={"source1": "source1", "source2": "source2"},
        root={
            "mixed_sources": {
                "source": "source1",
                "filter": "All",
                "source2": {
                    "source": "source2",
                    "filter": "All",
                },
            },
        },
    )

    await source1.text_messages(texts=["hello1", "hello2"])
    await source2.text_messages(
        texts=["hello source2 1", "hello source2 2", "hello source2 3"]
    )

    async def test():
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

        assert await ctx.read_texts(
            await ctx.listdir_set("/mixed_sources/source2", full_path=True)
        ) == {"hello source2 1", "hello source2 2", "hello source2 3"}

    await ctx.run_test(test, config)


@pytest.mark.asyncio
async def test_two_sources_3(
    ctx: TgmountIntegrationContext,
    source1: StorageEntity,
    source2: StorageEntity,
):
    """Recursive filter could be overwritten"""
    config = create_config(
        message_sources={"source1": "source1", "source2": "source2"},
        root={
            "source": {"source": "source1", "recursive": True},
            "dir1": {
                "dir2": {
                    "source1": {"filter": "All"},
                    "source2": {
                        "source": "source2",
                        "filter": "All",
                        "source1": {"filter": "All"},
                    },
                }
            },
        },
    )

    await source1.text_messages(texts=["hello1", "hello2"])
    await source2.text_messages(
        texts=["hello source2 1", "hello source2 2", "hello source2 3"]
    )

    async def test():
        assert await ctx.listdir_set("/") == {"dir1"}
        assert await ctx.listdir_set("/dir1") == {"dir2"}
        assert await ctx.listdir_set("/dir1/dir2") == {"source1", "source2"}
        assert await ctx.listdir_set("/dir1/dir2/source1") == {
            "1_message.txt",
            "2_message.txt",
        }

        assert await ctx.listdir_set("/dir1/dir2/source2") == {
            "1_message.txt",
            "2_message.txt",
            "3_message.txt",
            "source1",
        }

        assert await ctx.listdir_set("/dir1/dir2/source2/source1") == {
            "1_message.txt",
            "2_message.txt",
        }

    await ctx.run_test(test, config)
