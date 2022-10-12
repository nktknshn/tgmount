import asyncio
import os
import threading
from typing import Mapping, TypedDict

import telethon
from tests.integrational.integrational_helpers import DEFAULT_ROOT
import tgmount.config as config
import tgmount.tgclient as tg
from tgmount.main.util import read_tgapp_api
from tgmount import tglog
from tgmount.tgmount.builder import TgmountBuilder


# import os


Message = telethon.tl.custom.Message
Document = telethon.types.Document
Client = tg.TgmountTelegramClient


TESTING_CHANNEL = "tgmounttestingchannel"

# Props = Mapping
Props = TypedDict(
    "Props",
    debug=bool,
    ev0=threading.Event,
    ev1=threading.Event,
    cfg=config.Config,
)


def create_config(
    root: Mapping = DEFAULT_ROOT,
) -> config.Config:
    api_id, api_hash = read_tgapp_api()

    return config.Config(
        client=config.Client(api_id=api_id, api_hash=api_hash, session="tgfs"),
        message_sources=config.MessageSources(
            sources={"tmtc": config.MessageSource(entity=TESTING_CHANNEL)},
        ),
        caches=config.Caches(
            {
                "memory1": config.Cache(
                    type="memory", kwargs={"capacity": "50MB", "block_size": "128KB"}
                )
            }
        ),
        root=config.Root(root),
    )


def async_listdir(path: str):
    return asyncio.to_thread(os.listdir, path)


class MyTgmountBuilder(TgmountBuilder):
    def __init__(self, client_kwargs={}) -> None:
        super().__init__()
        self._client_kwargs = client_kwargs

    async def create_client(self, cfg: config.Config):
        return await super().create_client(cfg, **self._client_kwargs)


async def main_test1(props: Props, on_event):

    # on_event(props["ev0"], print_tasks)
    # on_event(props["ev1"], print_tasks)

    async def on_new_message(event):
        print(event)

    tglog.init_logging(props["debug"])

    test_logger = tglog.getLogger("main_test1")

    # tglog.getLogger("FileSystemOperations()").setLevel(logging.ERROR)
    # logging.getLogger("telethon").setLevel(logging.INFO)

    test_logger.debug("Building...")
    builder = MyTgmountBuilder(
        client_kwargs=dict(
            # sequential_updates=True,
        )
    )

    test_logger.debug("Creating...")
    tgm = await builder.create_tgmount(props["cfg"])

    # tgm.client.add_event_handler(
    #     on_new_message, events.NewMessage(chats=TESTING_CHANNEL)
    # )

    test_logger.debug("Auth...")
    await tgm.client.auth()

    # tgm.client.on(events.NewMessage(chats=TESTING_CHANNEL))(on_new_message)

    test_logger.debug("Creating FS...")
    await tgm.create_fs()

    test_logger.debug("Returng FS")

    return tgm.fs


class Client:
    def __init__(self, client, entity=TESTING_CHANNEL) -> None:
        self.client = client
        self.entity = entity

    async def send_message(self, **kwargs):
        return await self.client.send_message(self.entity, **kwargs)

    async def delete_messages(self, msg_ids: list[int], **kwargs):
        return await self.client.delete_messages(self.entity, msg_ids)
