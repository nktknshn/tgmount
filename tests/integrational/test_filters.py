import logging
import aiofiles

import pytest
import tgmount
from tests.helpers.mocked.mocked_storage import StorageEntity
from tests.integrational.helpers import create_config, mdict
from .fixtures import *

from tgmount.tgmount.filters import ByExtension, OnlyUniqueDocs


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
async def test_recursive_filter_3(
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


# OnlyUniqueDocs.logger.setLevel(logging.DEBUG)

# tgmount.tglog.getLogger("OnlyUniqueDocs()").setLevel(logging.DEBUG)


@pytest.mark.asyncio
async def test_recursive_filter_4(
    caplog,
    ctx: Context,
    source1: StorageEntity,
    source2: StorageEntity,
    files: FixtureFiles,
):
    # caplog.set_level(logging.DEBUG)

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
        text="Hummingbird", file=files.Hummingbird
    )

    await source1.document_file_message(text="same document", file=msg0.document)

    await source1.text_messages(texts=["hello1", "hello2"])

    async def test():
        assert await ctx.listdir_set("/source1") == {"all", "all2"}
        assert await ctx.listdir_set("/source1/all") == {"1_Hummingbird.jpg"}
        assert await ctx.listdir_set("/source1/all2") == {"1_Hummingbird.jpg"}

    await ctx.run_test(test, config)

    async def test2():
        """works without MessageWithDocument"""
        assert await ctx.listdir_set("/source1") == {"all", "all2"}
        assert await ctx.listdir_set("/source1/all") == {
            "1_Hummingbird.jpg",
            "3_message.txt",
            "4_message.txt",
        }
        assert await ctx.listdir_set("/source1/all2") == {
            "1_Hummingbird.jpg",
            "3_message.txt",
            "4_message.txt",
        }

    await ctx.run_test(
        test2,
        config.set_root(
            mdict(config.root.content)
            .update({"filter": ["OnlyUniqueDocs"]}, at="/source1/filter")
            .get()
        ),
    )


@pytest.mark.asyncio
async def test_recursive_filter_5(
    caplog,
    ctx: Context,
    source1: StorageEntity,
    source2: StorageEntity,
    files: FixtureFiles,
):
    """recrusive filters and filters sum up"""
    # ctx.debug = True
    ByExtension.logger.setLevel(logging.DEBUG)
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
                "another_filter": {
                    "filter": {
                        "filter": ["OnlyUniqueDocs"],
                        "recursive": True,
                    },
                    "producer": "PlainDir",
                    "subdir": {
                        "filter": "All",
                        "subsubdir": {
                            "filter": {"ByExtension": ".jpg"},
                        },
                    },
                },
            },
        },
    )

    msg0 = await source1.document_file_message(
        text="Hummingbird", file=files.Hummingbird
    )

    await source1.document_file_message(text="same document", file=msg0.document)
    await source1.text_messages(texts=["hello1", "hello2"])

    await source1.document_file_message(
        text="Tvrdý _ Havelka - Žiletky",
        file=files.music0,
        file_name="Artist1_song1.mp3",
    )

    async def test():
        # MessageWithDocument applied
        assert await ctx.listdir_set("/source1/all") == {
            "1_Hummingbird.jpg",
            "2_Hummingbird.jpg",
            "5_Artist1_song1.mp3",
        }

        # MessageWithDocument and OnlyUniqueDocs applied
        assert await ctx.listdir_set("/source1/another_filter") == {
            "1_Hummingbird.jpg",
            "5_Artist1_song1.mp3",
            "subdir",
        }

        # MessageWithDocument and OnlyUniqueDocs applied recursively
        assert await ctx.listdir_set("/source1/another_filter/subdir") == {
            "1_Hummingbird.jpg",
            "5_Artist1_song1.mp3",
            "subsubdir",
        }

        # MessageWithDocument and OnlyUniqueDocs and ByExtension(.jpg) applied
        assert await ctx.listdir_set("/source1/another_filter/subdir/subsubdir") == {
            "1_Hummingbird.jpg"
        }

    await ctx.run_test(test, config)


""" 
    await source1.audio_file_message(
        text="Tvrdý _ Havelka - Žiletky",
        file=files.music0,
        performer="Artist1",
        title="Song1",
        file_name="Artist1_song1.mp3",
        duration=666,
    )

    await source1.audio_file_message(
        file=files.music1,
        performer="Artist1",
        title="Song2",
        file_name="Artist1_song2.mp3",
        duration=666,
    )
 """
