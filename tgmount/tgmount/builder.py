import abc
from abc import abstractmethod
from collections.abc import Awaitable, Callable, Mapping
from typing import Type

from tgmount import config, tg_vfs, tgclient, vfs
from tgmount.cache import CacheFactory, CacheFactoryMemory
from tgmount.config import Config, ConfigValidator
from tgmount.tg_vfs.file_factory import FileFactory
from tgmount.tgclient import TelegramMessageSource, TgmountTelegramClient, guards
from tgmount.tgmount.wrappers import DirWrappersProvider
from tgmount.util import col, compose_guards

from .base2 import CreateRootContext, Tgmount
from .builderbase import TgmountBuilderBase
from .types import (
    CachesProviderProto,
    DirWrapperProviderProto,
    Filter,
    FilterProviderProto,
    TgmountError,
    TgmountRoot,
)

from .caches import CacheProvider


class FilterProvider(FilterProviderProto):

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

    def __init__(self) -> None:
        super().__init__()

    def get_filters(self) -> Mapping[str, Filter]:
        return {f.__name__: f.guard for f in self.filters}


class TgmountBuilder(TgmountBuilderBase):
    TelegramClient = tgclient.TgmountTelegramClient
    MessageSource = tgclient.TelegramMessageSource
    FilesSource = tgclient.TelegramFilesSource
    FileFactory = tg_vfs.FileFactory

    filters: FilterProviderProto = FilterProvider()
    caches: CachesProviderProto = CacheProvider()
    wrappers: DirWrapperProviderProto = DirWrappersProvider()
