from tgmount import cache, tgclient, vfs
from tgmount.tgclient.guards import MessageWithText
from tgmount.tgmount.file_factory.classifier import ClassifierDefault

from .tgmount_builderbase import TgmountBuilderBase
from .file_factory import FileFactoryDefault
from .providers.provider_caches import CachesProviderProto
from .providers.provider_filters import FilterProviderProto
from .providers.provider_sources import SourcesProvider
from .providers.provider_wrappers import DirWrapperProviderProto
from .tgmount_providers import (
    CachesProvider,
    DirWrappersProvider,
    FilterProvider,
    ProducersProvider,
)


class MyFileFactoryDefault(FileFactoryDefault[MessageWithText]):
    pass


MyFileFactoryDefault.register(
    klass=MessageWithText,
    filename=MessageWithText.filename,
    file_content=lambda m: vfs.text_content(m.text),
)


class MyClassifier(ClassifierDefault[MessageWithText]):
    pass


MyClassifier.classes.append(MessageWithText)


class TgmountBuilder(TgmountBuilderBase):
    TelegramClient = tgclient.TgmountTelegramClient
    MessageSource = tgclient.MessageSourceSimple
    FilesSource = tgclient.TelegramFilesSource
    FilesSourceCaching = cache.FilesSourceCaching
    FileFactory = MyFileFactoryDefault
    SourcesProvider = SourcesProvider

    classifier = ClassifierDefault()
    filters: FilterProviderProto = FilterProvider()
    caches: CachesProviderProto = CachesProvider()
    wrappers: DirWrapperProviderProto = DirWrappersProvider()
    producers = ProducersProvider()
