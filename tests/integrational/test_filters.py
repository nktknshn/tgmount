import aiofiles

import pytest
import tgmount
from tests.helpers.mocked.mocked_storage import StorageEntity
from tests.integrational.helpers import create_config, mdict
from .fixtures import *


@pytest.mark.asyncio
async def test_recursive_filter_1(
    caplog, ctx: Context, source1: StorageEntity, source2: StorageEntity
):
    """recursive filter doesn't produce files in the folder it was declared i"""
    config = create_config(
        message_sources={"source1": "source1", "source2": "source2"},
        root={
            "source1": {
                "source": {"source": "source1", "recursive": True},
                "filter": {"filter": ["MessageWithDocument"], "recursive": True},
            },
        },
    )

    # await source1.text_messages(texts=["hello1", "hello2"])

    msg0 = await source1.document_file_message(
        text="document1", file="tests/fixtures/Hummingbird.jpg"
    )

    # msg1 = await source1.document_file_message(text="document1", file=msg0.document)

    async def test():
        assert await ctx.listdir_set("/source1") == set()

    await ctx.run_test(test, config)


@pytest.mark.asyncio
async def test_recursive_filter_2(
    caplog, ctx: Context, source1: StorageEntity, source2: StorageEntity
):
    """recursive filter produce files in the folder it was declared in if producer specified"""
    config = create_config(
        message_sources={"source1": "source1", "source2": "source2"},
        root={
            "source1": {
                "source": {"source": "source1", "recursive": True},
                "filter": {"filter": ["MessageWithDocument"], "recursive": True},
                "producer": "PlainDir",
            },
        },
    )

    msg0 = await source1.document_file_message(
        text="document1", file="tests/fixtures/Hummingbird.jpg"
    )
    await source1.text_messages(texts=["hello1", "hello2"])

    # msg1 = await source1.document_file_message(text="document1", file=msg0.document)

    async def test():
        assert await ctx.listdir_set("/source1") == {"1_Hummingbird.jpg"}

    await ctx.run_test(test, config)


@pytest.mark.asyncio
async def test_recursive_filter_4(
    caplog, ctx: Context, source1: StorageEntity, source2: StorageEntity
):
    """filter 'All' doesn't cancel recursive filter"""
    config = create_config(
        message_sources={"source1": "source1", "source2": "source2"},
        root={
            "source1": {
                "source": {"source": "source1", "recursive": True},
                "filter": {
                    "filter": ["MessageWithDocument"],
                    "recursive": True,
                },
                "all": {"filter": "All"},
                "all2": {"producer": "PlainDir"},
            },
        },
    )

    msg0 = await source1.document_file_message(
        text="Hummingbird", file="tests/fixtures/Hummingbird.jpg"
    )

    await source1.document_file_message(text="same document", file=msg0.document)

    await source1.text_messages(texts=["hello1", "hello2"])

    async def test():
        assert await ctx.listdir_set("/source1") == {"all", "all2"}
        assert await ctx.listdir_set("/source1/all") == {
            "1_Hummingbird.jpg",
            "2_Hummingbird.jpg",
        }
        assert await ctx.listdir_set("/source1/all2") == {
            "1_Hummingbird.jpg",
            "2_Hummingbird.jpg",
        }

    await ctx.run_test(test, config)


@pytest.mark.asyncio
async def test_recursive_filter_3(
    caplog, ctx: Context, source1: StorageEntity, source2: StorageEntity
):
    """OnlyUniqueDocs works"""
    config = create_config(
        message_sources={"source1": "source1", "source2": "source2"},
        root={
            "source1": {
                "source": {"source": "source1", "recursive": True},
                "filter": {
                    "filter": ["MessageWithDocument", "OnlyUniqueDocs"],
                    "recursive": True,
                },
                "all": {"filter": "All"},
                "all2": {"producer": "PlainDir"},
            },
        },
    )

    msg0 = await source1.document_file_message(
        text="Hummingbird", file="tests/fixtures/Hummingbird.jpg"
    )

    await source1.document_file_message(text="same document", file=msg0.document)

    await source1.text_messages(texts=["hello1", "hello2"])

    async def test():
        assert await ctx.listdir_set("/source1") == {"all", "all2"}
        assert await ctx.listdir_set("/source1/all") == {"1_Hummingbird.jpg"}
        assert await ctx.listdir_set("/source1/all2") == {"1_Hummingbird.jpg"}

    await ctx.run_test(test, config)
