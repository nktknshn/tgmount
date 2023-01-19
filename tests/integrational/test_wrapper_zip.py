import logging
import os
import pytest

from pprint import pprint
from tgmount import vfs, zip as z
from tests.integrational.helpers import mdict
from tests.integrational.integrational_configs import create_config
from tgmount.tgmount.vfs_tree_types import (
    TreeEventNewDirs,
    TreeEventNewItems,
    TreeEventRemovedDirs,
)
from tgmount.tgmount.wrappers.wrapper_exclude_empty_dirs import WrapperEmpty

from .fixtures import *
from .context import Context

from ..logger import logger as _logger


root_cfg1 = {
    "source": {
        "source": "source1",
        "recursive": True,
    },
    "filter": "MessageWithZip",
    "wrappers": {
        "ZipsAsDirs": {
            "skip_single_root_subfolder": False,
        }
    },
}


async def prepare_ctx(fixtures: Fixtures):

    ctx = Context.from_fixtures(fixtures)

    config = create_config(
        message_sources={"source1": "source1"},
        root=root_cfg1,
    )

    ctx.set_config(config)

    await ctx.source1.document(file=ctx.files.zip_debrecen.path)
    await ctx.source1.document(file=ctx.files.zip_bandcamp.path)

    return ctx


@pytest.mark.asyncio
async def test_simple1(fixtures: Fixtures):
    ctx = await prepare_ctx(fixtures)
    fname1 = ctx.files.zip_debrecen.basename
    fname2 = ctx.files.zip_bandcamp.basename

    zf1 = await ctx.files.zip_debrecen.zip_file()
    zf2 = await ctx.files.zip_bandcamp.zip_file()

    fls1 = z.zip_ls(zf1)
    fls2 = z.zip_ls(zf2)

    assert fls1
    assert fls2

    async def test():
        assert await ctx.listdir_set("/") == {
            f"1_{fname1}",
            f"2_{fname2}",
        }

        assert await ctx.listdir_set("/", f"1_{fname1}") == set(fls1.keys())

        assert await ctx.listdir_set("/", f"2_{fname2}") == set(fls2.keys())

        await ctx.client.delete_messages(ctx.source1.entity_id, msg_ids=[1])

        assert await ctx.listdir_set("/") == {
            f"2_{fname2}",
        }

    await ctx.run_test(test)


@pytest.mark.asyncio
async def test_simple2(fixtures: Fixtures):

    ctx = await prepare_ctx(fixtures)

    fname1 = ctx.files.zip_debrecen.basename
    fname2 = ctx.files.zip_bandcamp.basename

    zf1 = await ctx.files.zip_debrecen.zip_file()
    zf2 = await ctx.files.zip_bandcamp.zip_file()

    fls1 = z.zip_ls(zf1, path=["2010_Debrecen"])
    fls2 = z.zip_ls(zf2)

    assert fls1
    assert fls2

    async def test():
        assert await ctx.listdir_set("/") == {
            f"1_2010_Debrecen",
            f"2_{fname2}",
        }

        assert await ctx.listdir_set("/", f"1_2010_Debrecen") == set(fls1.keys())
        assert await ctx.listdir_set("/", f"2_{fname2}") == set(fls2.keys())

        await ctx.client.delete_messages(ctx.source1.entity_id, msg_ids=[1])

        assert await ctx.listdir_set("/") == {
            f"2_{fname2}",
        }

    await ctx.run_test(
        test,
        cfg_or_root=mdict(root_cfg1)
        .update(
            {"skip_single_root_subfolder": True},
            at="/wrappers/ZipsAsDirs",
        )
        .get(),
    )


@pytest.mark.asyncio
async def test_simple3(fixtures: Fixtures):

    ctx = await prepare_ctx(fixtures)

    fname1 = ctx.files.zip_debrecen.basename
    fname2 = ctx.files.zip_bandcamp.basename

    async def test():
        assert await ctx.listdir_set("/") == {
            f"1_{fname1}",
            f"1_{fname1}_unzipped",
            f"2_{fname2}",
            f"2_{fname2}_unzipped",
        }

        await ctx.client.delete_messages(ctx.source1.entity_id, msg_ids=[1])

        assert await ctx.listdir_set("/") == {
            f"2_{fname2}",
            f"2_{fname2}_unzipped",
        }

    await ctx.run_test(
        test,
        cfg_or_root=mdict(root_cfg1)
        .update(
            {"hide_zip_files": False},
            at="/wrappers/ZipsAsDirs",
        )
        .get(),
    )


@pytest.mark.asyncio
async def test_simple4(fixtures: Fixtures):

    ctx = await prepare_ctx(fixtures)

    fname1 = ctx.files.zip_debrecen.basename
    fname2 = ctx.files.zip_bandcamp.basename

    async def test():
        assert await ctx.listdir_set("/") == {
            f"1_{fname1}",
            f"1_2010_Debrecen",
            f"2_{fname2}",
            f"2_{fname2}_unzipped",
        }

    await ctx.run_test(
        test,
        cfg_or_root=mdict(root_cfg1)
        .update(
            {"hide_zip_files": False, "skip_single_root_subfolder": True},
            at="/wrappers/ZipsAsDirs",
        )
        .get(),
    )


# @pytest.mark.asyncio
# async def test_fix_id3v1(fixtures: Fixtures):

#     ctx = await prepare_ctx(fixtures)

#     fname1 = ctx.files.zip_debrecen.basename
#     fname2 = ctx.files.zip_bandcamp.basename

#     async def test():
#         assert await ctx.listdir_set("/") == {
#             f"1_{fname1}",
#             f"1_2010_Debrecen",
#             f"2_{fname2}",
#             f"2_{fname2}_unzipped",
#         }

#     await ctx.run_test(
#         test,
#         cfg_or_root=mdict(root_cfg1)
#         .update(
#             {"hide_zip_files": False, "skip_single_root_subfolder": True},
#             at="/wrappers/ZipsAsDirs",
#         )
#         .get(),
#     )
