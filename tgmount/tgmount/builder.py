from collections.abc import Mapping
from dataclasses import dataclass
from typing import Optional, TypeGuard

import telethon
from telethon.tl.custom import Message

from tgmount import cache, tg_vfs, tgclient, vfs
from tgmount.tg_vfs.classifier import ClassifierBase
from tgmount.tg_vfs.filefactorybase import (
    FileFactoryBase,
    FileFactoryDefault,
    FileFactorySupportedTypes,
)
from tgmount.tg_vfs.types import FileContentProviderProto
from tgmount.tgclient.guards import MessageWithText
from tgmount.tgmount.providers import DirWrappersProvider, FilterProvider

from .builderbase import TgmountBuilderBase
from .caches import CachesProviderProto
from .filters import FilterProviderProto
from .providers import CachesProvider, VfsProducersProvider
from .provider_sources import SourcesProvider
from .wrappers import DirWrapperProviderProto


class MyFileFactoryDefault(
    FileFactoryDefault,
    FileFactoryBase[FileFactorySupportedTypes | MessageWithText],
):
    def __init__(self, files_source: FileContentProviderProto, extra) -> None:
        super().__init__(files_source, extra)

        # async def text_message_content(m: MessageWithText):
        #     sender = await m.get_sender()
        #     name = telethon.utils.get_display_name(sender)

        #     return vfs.text_content(f"{name}: {m.text.encode('utf-8')}")

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
    SourcesProvider = SourcesProvider

    classifier = ClassifierBase()
    filters: FilterProviderProto = FilterProvider()
    caches: CachesProviderProto = CachesProvider()
    wrappers: DirWrapperProviderProto = DirWrappersProvider()
    producers = VfsProducersProvider()
