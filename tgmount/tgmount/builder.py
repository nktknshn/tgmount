from dataclasses import dataclass
from collections.abc import Mapping
from typing import Optional, TypeGuard

from telethon.tl.custom import Message

from tgmount import tg_vfs, tgclient, vfs, cache
from tgmount.tg_vfs.classifier import ClassifierBase
from tgmount.tg_vfs.types import FileContentProviderProto
from tgmount.tgclient.guards import MessageWithText
from tgmount.tgmount.providers import DirWrappersProvider, FilterProvider

from .builderbase import TgmountBuilderBase
from .providers import CachesProvider, TreeProducersProvider
from .caches import CachesProviderProto
from .wrappers import DirWrapperProviderProto
from .filters import FilterProviderProto
from tgmount.tg_vfs.filefactorybase import (
    FileFactoryBase,
    FileFactoryDefault,
    FileFactorySupportedTypes,
)


class MyFileFactoryDefault(
    FileFactoryDefault,
    FileFactoryBase[FileFactorySupportedTypes | MessageWithText],
):
    def __init__(self, files_source: FileContentProviderProto, extra) -> None:
        super().__init__(files_source, extra)
        self.register(
            klass=MessageWithText,
            filename=MessageWithText.filename,
            file_content=lambda m: vfs.text_content(m.text),
        )


class TgmountBuilder(TgmountBuilderBase):
    TelegramClient = tgclient.TgmountTelegramClient
    MessageSource = tgclient.TelegramMessageSource
    FilesSource = tgclient.TelegramFilesSource
    FilesSourceCaching = cache.FilesSourceCaching
    FileFactory = MyFileFactoryDefault

    classifier = ClassifierBase()
    filters: FilterProviderProto = FilterProvider()
    caches: CachesProviderProto = CachesProvider()
    wrappers: DirWrapperProviderProto = DirWrappersProvider()
    producers = TreeProducersProvider()
