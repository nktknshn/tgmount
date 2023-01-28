from typing import Mapping
from tgmount import cache, tgclient, vfs
from tgmount.tgclient.guards import MessageWithReactions, MessageWithText
from tgmount.tgclient.message_types import MessageProto
from tgmount.tgmount.cached_filefactory_factory import CacheFileFactoryFactory
from tgmount.tgmount.file_factory.classifier import ClassifierDefault
from tgmount.tgmount.file_factory.filefactory import FileFactorySupportedTypes
from tgmount.tgmount.producers.producer_by_sender import get_message_sender_display_name
from tgmount.util import yes

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
    def copy_with_props(self, factory_props):
        return MyFileFactoryDefault(
            files_source=self._files_source, factory_props=factory_props
        )

    async def file(
        self,
        supported_item: FileFactorySupportedTypes | MessageWithText,
        name=None,
        factory_props=None,
    ) -> vfs.FileLike:
        return await super().file(supported_item, name, factory_props)

    async def file_content(
        self,
        supported_item: FileFactorySupportedTypes | MessageWithText,
        factory_props=None,
    ) -> vfs.FileContentProto:
        return await super().file_content(supported_item, factory_props)


class MessageWithTextContent:
    @staticmethod
    async def make_string(message: MessageWithText) -> str:
        result = ""

        if yes(message.date):
            result += message.date.ctime()
        else:
            result += "no date"

        result += "\n"

        sender_name = await get_message_sender_display_name(message, True)

        if yes(sender_name):
            result += f"from: {sender_name}\n"
        else:
            result += f"from: Deleted Account\n"

        result += ""
        result += message.text
        result += "\n"

        return result

    @staticmethod
    async def create_content(m: MessageWithText):
        return vfs.text_content(await MessageWithTextContent.make_string(m))


MyFileFactoryDefault.register(
    klass=MessageWithText,
    filename=MessageWithText.filename,
    file_content=MessageWithTextContent.create_content,
)


class MyClassifier(ClassifierDefault[MessageWithText]):
    pass


MyClassifier.register(MessageWithText)

# cccc = tgclient.TgmountTelegramClient()
# a: tgclient.client_types.TgmountTelegramClientReaderProto = cccc


class TgmountBuilder(TgmountBuilderBase):
    def __init__(self, mount_texts=True) -> None:
        if not mount_texts:
            MyFileFactoryDefault.unregister(MessageWithText)

    TelegramClient = tgclient.TgmountTelegramClient
    """ Class used for telegram client """

    MessageSource = tgclient.MessageSource
    """ class used for a message source """

    MessageSourceProvider = SourcesProvider
    """ Source provider """

    FilesSource = tgclient.TelegramFilesSource
    """ Class used for content provider """

    FilesSourceCached = cache.FilesSourceCached
    """ class used for caching content provider """

    CacheFactory = CacheFileFactoryFactory

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
