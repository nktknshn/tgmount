import copy
import logging
import os
from typing import Mapping

import pytest
import tgmount
from tests.helpers.mocked.mocked_storage import StorageEntity
from tests.integrational.helpers import TESTING_CHANNEL, create_config

from ..helpers.mocked.mocked_message import MockedMessage, MockedSender
from .integrational_helpers import BY_SENDER, DEFAULT_ROOT, UNPACKED
from .integrational_test import (
    TgmountIntegrationContext,
    TgmountIntegrationTest,
    mnt_dir,
)


class build_root:
    def __init__(self, root: Mapping) -> None:
        self._root: dict = copy.deepcopy(dict(root))
        self._current_dict = self._root
        self._path = []

    def enter(self, key: str | None = None):
        if key is None:
            self._path = []
            self._current_dict = self._root
        else:
            self._path.append(key)
            self._current_dict = self._current_dict[key]
        return self

    def update(self, d: dict):
        self._current_dict.update(copy.deepcopy(d))
        return self

    def go(self):
        pass

    def get(self):
        return self._root


@pytest.fixture
def ctx(mnt_dir):
    return TgmountIntegrationContext(mnt_dir)


@pytest.fixture
def tmtc(ctx):
    return ctx.storage.get_entity(TESTING_CHANNEL)


# build_root(DEFAULT_ROOT).enter("tmtc").update({"all": {"filter": "All"}})

# DEFAULT_ROOT: Mapping = {
#     "tmtc": {"source": {"source": "tmtc"}},
# }


@pytest.mark.asyncio
async def test_fails_empty_root(caplog, ctx, tmtc: StorageEntity):
    async def test():
        pass

    with pytest.raises(tgmount.config.ConfigError):
        await ctx.run_test(test, {})


@pytest.mark.asyncio
async def test_simple1(caplog, ctx, tmtc: StorageEntity):

    await tmtc.message(message_text="hello1")
    await tmtc.message(message_text="hello2")
    await tmtc.message(message_text="hello3")

    async def test():
        assert await ctx.listdir_set("/") == set({"tmtc"})
        assert await ctx.listdir_set("/tmtc") == {
            "1_message.txt",
            "2_message.txt",
            "3_message.txt",
        }

    await ctx.run_test(test, {"tmtc": {"source": "tmtc"}})
    await ctx.run_test(test, {"tmtc": {"source": {"source": "tmtc"}}})


@pytest.mark.asyncio
async def test_recursive_source_empty(caplog, ctx, tmtc: StorageEntity):
    root = {"tmtc": {"source": {"source": "tmtc", "recursive": True}}}
    await tmtc.message(message_text="hello1")

    async def test():
        assert await ctx.listdir_set("/") == set({"tmtc"})
        assert await ctx.listdir_set("/tmtc") == set()

    await ctx.run_test(test, root)


# tgmount.tglog.getLogger("TgmountConfigReader()").setLevel(logging.DEBUG)


@pytest.mark.asyncio
async def test_recursive_source_with_filter(caplog, ctx, tmtc: StorageEntity):
    root = {
        "tmtc": {
            "source": {"source": "tmtc", "recursive": True},
            "filter": "All",
        }
    }

    await tmtc.message(message_text="hello1")
    await tmtc.message(message_text="hello2")
    await tmtc.message(message_text="hello3")

    async def test():
        assert await ctx.listdir_set("/") == set({"tmtc"})
        assert await ctx.listdir_set("/tmtc") == {
            "1_message.txt",
            "2_message.txt",
            "3_message.txt",
        }

    await ctx.run_test(test, root)
