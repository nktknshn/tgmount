import abc
from abc import abstractmethod
from collections.abc import Awaitable, Callable, Mapping
from typing import Type
from tgmount.config import Config, ConfigValidator
from tgmount import config
from tgmount.tg_vfs.file_factory import FileFactory
from tgmount.tgclient import TgmountTelegramClient, TelegramMessageSource
from tgmount.tgmount import TgmountBase
from tgmount.util import col, compose_guards
from tgmount import vfs, tg_vfs, tgclient

from .types import Filter, TgmountRoot, FilterProviderProto
from .base2 import CreateRootContext, Tgmount
from .builderbase import TgmountBuilderBase
from tgmount.tgclient import TelegramMessageSource, guards

filters = [
    guards.MessageWithCompressedPhoto,
    guards.MessageWithVideo,
    guards.MessageWithDocument,
    guards.MessageWithDocumentImage,
    guards.MessageWithVoice,
    guards.MessageWithKruzhochek,
    guards.MessageWithZip,
    guards.MessageWithMusic,
    guards.MessageWithAnimated,
    guards.MessageWithOtherDocument,
    guards.MessageWithSticker,
    guards.MessageWithVideoCompressed,
]


class FilterProvider(FilterProviderProto):
    def __init__(self) -> None:
        super().__init__()

    def get_filters(self) -> Mapping[str, Filter]:
        return {f.__name__: f.guard for f in filters}


class TgmountBuilder(TgmountBuilderBase):
    TelegramClient = tgclient.TgmountTelegramClient
    MessageSource = tgclient.TelegramMessageSource
    FilesSource = tgclient.TelegramFilesSource
    FileFactory = tg_vfs.FileFactory

    filters: FilterProviderProto = FilterProvider()
