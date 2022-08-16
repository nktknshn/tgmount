# import pytest
# import pytest_asyncio
# from tgmount.tgclient import TgmountTelegramClient
# from tgmount.main.util import read_tgapp_api


# @pytest.fixture
# def tgapp_api():
#     return read_tgapp_api()


# Client = TgmountTelegramClient


# @pytest_asyncio.fixture
# async def tgclient(tgapp_api):
#     client = TgmountTelegramClient("tgfs", tgapp_api[0], tgapp_api[1])

#     await client.auth()

#     yield client

#     cor = client.disconnect()

#     if cor is not None:
#         await cor
