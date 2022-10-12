import logging
import aiofiles

import pytest
import tgmount
from tests.helpers.mocked.mocked_storage import StorageEntity
from tests.integrational.helpers import create_config, mdict
from .fixtures import *

from tgmount.tgmount.filters import ByExtension, OnlyUniqueDocs


@pytest.mark.asyncio
async def test_filters_1(
    ctx: Context,
    source1: StorageEntity,
    source2: StorageEntity,
    files: FixtureFiles,
):
    """Test different kinds of filters"""
    config = create_config(
        message_sources={"source1": "source1", "source2": "source2"},
        root={
            "source1": {
                "source": {"source": "source1", "recursive": True},
                "all": {"producer": "PlainDir"},
                "docs-with-text": {
                    "filter": ["MessageWithText", "MessageWithDocument"]
                },
                "text-and-pictures": {
                    "filter": {"Union": ["MessageWithText", "MessageWithDocumentImage"]}
                },
            },
        },
    )

    text_msgs = await source1.text_messages(["message 1", "message 2", "message 3"])

    docs_msgs = await source1.files(
        files=[
            {"file": files.Hummingbird, "image": True},
            {"file": files.picture1, "text": "this is picture1", "image": True},
            {"file": files.picture1, "image": True},
            files.music0,
            files.music1,
            files.music2,
        ]
    )

    async def test():
        text_files = list(f"{m.id}_message.txt" for m in text_msgs)
        doc_files = list(f"{m.id}_{m.file.name}" for m in docs_msgs)

        assert await ctx.listdir_set("/source1/all") == set(doc_files) | set(text_files)
        assert await ctx.listdir_set("/source1/docs-with-text") == {doc_files[1]}

        assert await ctx.listdir_set("/source1/text-and-pictures") == set(
            doc_files[:3]
        ) | set(text_files)

    await ctx.run_test(test, config)
