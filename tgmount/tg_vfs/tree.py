from typing import Callable, Mapping, TypeGuard, TypeVar, cast

from telethon.tl.custom import Message
from tgmount import fs, vfs
from tgmount.cache import CacheFactoryMemory, FilesSourceCaching
from tgmount.tg_vfs import TelegramFilesSource
from tgmount.tg_vfs.helpers import message_tree
from tgmount.tg_vfs.mixins import (
    ContentFunc,
    FileContentProvider,
    FileFunc,
    FileFuncSupported,
)
from tgmount.tg_vfs.types import InputSourceItem
from tgmount.tgclient import TgmountTelegramClient
from tgmount.tgclient.search.filtering.guards import *
from tgmount.tgclient.search.filtering.guards import (
    MessageWithCompressedPhoto,
    MessageWithDocumentImage,
)
from tgmount.vfs.dir import FsSourceTree, FsSourceTreeValue
from tgmount.vfs.types.dir import DirContent, DirContentProto
from tgmount.vfs.types.file import FileContentProto

from ._tree.types import MessagesTree, MessagesTreeHandlerProto, MessagesTreeValue, Virt
from . import helpers

T = TypeVar("T", bound=FileFuncSupported)


class FileFactory(
    FileFunc,
    ContentFunc,
):
    def __init__(self, files_source: FileContentProvider) -> None:
        self._files_source = files_source

    def file(
        self,
        message: FileFuncSupported,
    ) -> vfs.FileLike:
        return FileFunc.file(self, message)

    def nfile(self, namef: Callable[[T], str]) -> Callable[[T], vfs.FileLike]:
        return lambda message: FileFunc.file(self, message, namef(message))

    def file_content(
        self, message: Message, input_item: InputSourceItem
    ) -> vfs.FileContent:
        return self._files_source.file_content(message, input_item)

    def create_tree(
        self, tree: MessagesTree | MessagesTreeValue
    ) -> FsSourceTree | FsSourceTreeValue:

        walker = message_tree.MessagesTreeWalker(self)

        if helpers.is_tree(tree):
            return helpers.walk_tree(
                tree,
                message_tree.messages_tree_walker(walker),
            )

        return helpers.walk_value(tree, message_tree.messages_tree_walker(walker))


class Tgmount:
    def __init__(
        self,
        vfs_root: vfs.VfsRoot,
        ops: fs.FileSystemOperations,
    ) -> None:
        self._vfs_root = vfs_root
        self._ops = ops

    async def process_event(self, event):
        pass
