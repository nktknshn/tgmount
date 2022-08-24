from collections.abc import Mapping

from tgmount import tg_vfs, tgclient
from tgmount.tgclient import guards
from tgmount.tgmount.providers import DirWrappersProvider, FilterProvider

from .builderbase import TgmountBuilderBase
from .types import (
    CachesProviderProto,
    Filter,
    FilterProviderProto,
)
from .wrappers import DirWrapperProviderProto

from .providers import CachesProvider, TreeProducersProvider


class TgmountBuilder(TgmountBuilderBase):
    TelegramClient = tgclient.TgmountTelegramClient
    MessageSource = tgclient.TelegramMessageSource
    FilesSource = tgclient.TelegramFilesSource
    FileFactory = tg_vfs.FileFactory

    filters: FilterProviderProto = FilterProvider()
    caches: CachesProviderProto = CachesProvider()
    wrappers: DirWrapperProviderProto = DirWrappersProvider()
    producers = TreeProducersProvider()
