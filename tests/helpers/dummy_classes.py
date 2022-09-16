import os
from typing import Any, Callable, Optional

import random
from dataclasses import dataclass, field
import pytest
import pytest_asyncio
from telethon.tl.custom.message import Message, File
from tgmount.tg_vfs.types import FileContentProviderProto
from tgmount.tgclient.client import TgmountTelegramClient
from tgmount.tgclient.message_source import (
    TelegramMessageSourceSimple,
)


from tgmount import vfs
from tgmount.tgmount.vfs_structure_types import VfsStructureProto
from tgmount.tgmount.types import CreateRootResources
from tgmount.tgmount.builder import TgmountBuilder
from ..config.fixtures import config_from_file


class DummyFile(File):
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self):
        return self._name

    @property
    def media(self):
        return None

    @property
    def ext(self):
        return os.path.splitext(self._name)[1]


rnd = lambda max: lambda: int(max * random.random())


@dataclass
class DummyDocument:
    size: int = 666
    id: int = field(default_factory=rnd(100000))
    access_hash: int = field(default_factory=rnd(100000))
    file_reference: bytes = field(default_factory=bytes)
    attributes: dict = field(default_factory=dict)


messages_count = 0


def next_message_id():
    global messages_count
    messages_count += 1
    return messages_count


class DummyMessage(Message):
    class Sender:
        username: str | None

    def __repr__(self) -> str:
        return f"DummyMessage({self.id})"

    def __init__(self, *, username=None, text=None, file=None) -> None:

        super().__init__(next_message_id())

        self.text = text

        self._sender = DummyMessage.Sender()
        self._sender.username = username
        self._file = file

        self._document = DummyDocument() if file else None

    @property
    def file(self):
        return self._file

    @property
    def document(self):
        return self._document

    async def get_sender(self):
        return self._sender

    def to_dict(self):
        return {"id": self.id, "document_id": None}


class DummyTgmountTelegramClient(TgmountTelegramClient):
    def __init__(self, *args, **kwargs):
        pass


class DummyFileSource(FileContentProviderProto):
    def __init__(self, client) -> None:
        pass

    def file_content(self, message):
        return vfs.text_content("dummy content")


class DummyMessageSource(TelegramMessageSourceSimple):
    def __init__(self, *args, **kwargs):
        super().__init__()
        # self._chat_id = chat_id

    async def notify(self, *args):
        for listener in self._listeners:
            # print(f"Notifying {listener}")
            await listener(self, *args)

    def subscribe(self, listener):
        # print(f"Subscribing {listener}")
        return super().subscribe(listener)

    def unsubscribe(self, listener):
        return super().subscribe(listener)


class DummyTgmountBuilder(TgmountBuilder):
    TelegramClient = DummyTgmountTelegramClient
    MessageSource = DummyMessageSource
    FilesSource = DummyFileSource

    _resources: CreateRootResources

    def __init__(self) -> None:
        super().__init__()

    # classifier = DummyClassifier()
    async def create_resources(self, client, cfg):
        resources = await super().create_resources(client, cfg)
        self._resources = resources
        return resources

    def get_source(self, source_name: str) -> DummyMessageSource:
        return self._resources.sources[source_name]  # type: ignore
