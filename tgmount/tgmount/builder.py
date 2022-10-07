from tgmount import cache, tgclient, vfs
from tgmount.tgclient.guards import MessageWithText

from .builderbase import TgmountBuilderBase
from .file_factory import ClassifierBase
from .file_factory.filefactorybase import (
    FileFactoryBase,
    FileFactoryDefault,
    FileFactorySupportedTypes,
)
from .file_factory.types import FileContentProviderProto
from .tgmount_providers import (
    CachesProvider,
    DirWrappersProvider,
    FilterProvider,
    ProducersProvider,
)
from .providers.provider_caches import CachesProviderProto
from .providers.provider_filters import FilterProviderProto
from .providers.provider_sources import SourcesProvider
from .providers.provider_wrappers import DirWrapperProviderProto


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
    producers = ProducersProvider()
