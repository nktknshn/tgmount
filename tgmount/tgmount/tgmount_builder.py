from tgmount import cache, tgclient, vfs
from tgmount.tgclient.guards import MessageWithReactions, MessageWithText
from tgmount.tgmount.file_factory.classifier import ClassifierDefault

from .tgmount_builderbase import TgmountBuilderBase
from .file_factory import FileFactoryDefault
from .providers.provider_filters import FilterProviderProto
from .providers.provider_sources import SourcesProvider
from .tgmount_providers import (
    CachesProvider,
    VfsWrappersProvider,
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


def reactions_file_name():
    pass


MyFileFactoryDefault.register(
    klass=MessageWithReactions,
    filename=MessageWithText.filename,
    file_content=lambda m: vfs.text_content(m.text),
)


class MyClassifier(ClassifierDefault[MessageWithText]):
    pass


MyClassifier.register(MessageWithText)


class TgmountBuilder(TgmountBuilderBase):
    TelegramClient = tgclient.TgmountTelegramClient
    """ Class used for telegram client """

    MessageSource = tgclient.MessageSource
    """ class used for a message source """

    MessageSourceProvider = SourcesProvider
    """ Source provider """

    FilesSource = tgclient.TelegramFilesSource
    """ Class used for content provider """

    FilesSourceCaching = cache.FilesSourceCaching
    """ class used for caching content provider """

    FileFactory = MyFileFactoryDefault
    """ Class that constructs file from messages """

    classifier = MyClassifier()
    """ classifies messages  """

    filters: FilterProviderProto = FilterProvider()
    """ provides messages filters  """

    wrappers: VfsWrappersProvider = VfsWrappersProvider()
    """ provides Vfs content wrappers """

    producers = ProducersProvider()
    """ providers vfs content producers  """

    caches = CachesProvider()
    """ provider caches """
