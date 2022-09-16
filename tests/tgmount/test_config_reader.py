import pytest
from tgmount import vfs
from telethon.tl.custom import Message

from tgmount.tg_vfs import file_factory
from tgmount.tg_vfs.classifier import ClassifierBase
from tgmount.tg_vfs.filefactorybase import FileFactoryDefault
from tgmount.tg_vfs.types import FileContentProviderProto
from tgmount.tgclient.message_source import Set, MessageSourceProto
from tgmount.tgmount.providers import (
    DirWrappersProvider,
    FilterProvider,
)
from tgmount.tgmount.tgmount_root_config_reader import TgmountConfigReader
from tgmount.config import Config, ConfigValidator
from tgmount.tgmount.types import CreateRootResources
from tgmount.tgclient import MessageSourceProto

from ..config.fixtures import config_from_file

import logging

logger = logging.getLogger("test_config_reader")


class DummyFileSource(FileContentProviderProto):
    async def file_content(self, message):
        return vfs.text_content("dummy content")


class DummyMessageSource(MessageSourceProto):
    async def get_messages(self) -> Set[Message]:
        return frozenset()
