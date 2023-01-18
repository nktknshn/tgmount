import pytest
import pytest_asyncio
import tgmount.tgclient as tg
from tgmount import vfs
from tgmount.main.util import read_tgapp_api


@pytest_asyncio.fixture
def tgapp_api():
    return read_tgapp_api()


@pytest_asyncio.fixture
async def tgclient_second():
    tgapp_api = read_tgapp_api(tgapp_file="tgapp2.txt")
    client = tg.TgmountTelegramClient(
        "tgfs2",
        tgapp_api[0],
        tgapp_api[1],
        receive_updates=False,
    )
    await client.auth()
    yield client
    await client.disconnect()
