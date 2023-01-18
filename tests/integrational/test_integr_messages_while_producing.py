import logging

import pytest
import pytest_asyncio
from tests.integrational.helpers import concurrentlys
from tests.integrational.integrational_configs import ORGRANIZED2, create_config

from .fixtures import *
from .context import Context


@pytest.mark.asyncio
async def test_message_while_producing(
    fixtures: Fixtures,
):
    """Tests updates of the tree"""
    ctx = Context.from_fixtures(fixtures)

    config = create_config(
        message_sources={"source1": "source1", "source2": "source2"},
        root={
            "source1": ORGRANIZED2,
            "source2": ORGRANIZED2,
        },
    )

    ctx.set_config(config)
    ctx.debug = logging.INFO

    ctx.create_senders(3)

    await ctx.send_text_messages(10)
    # await ctx.send_docs(10)

    expected_dirs = ctx.expected_dirs
    senders = ctx.senders
    [sender1, sender2, *_] = ctx.senders.keys()

    source1 = ctx.source1
    source2 = ctx.source2

    files = fixtures.files

    tgm = await ctx.create_tgmount()

    await concurrentlys(
        tgm.create_fs(),
        ctx.client.sender(sender1).send_message(
            ctx.source1.entity_id, "Message 1 from source 1"
        ),
        ctx.client.sender(sender2).send_message(
            ctx.source2.entity_id, "Message 1 from source 2"
        ),
    )
