from .types import FileContentProto
from .tree.message_tree import TreeCreator
from tgmount.tgclient import guards
from tgmount import vfs
from .file_factory_mixin import FileFactoryMixin


class FileFactory(
    TreeCreator,
    FileFactoryMixin,
):
    def __init__(self, files_source: FileContentProto) -> None:
        self._files_source = files_source

    def file_content(self, message: guards.MessageDownloadable) -> vfs.FileContent:
        return self._files_source.file_content(message)
