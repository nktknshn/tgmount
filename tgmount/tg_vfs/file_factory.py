from typing import Callable, Mapping, TypeGuard, TypeVar, cast

from telethon.tl.custom import Message
from tgmount import vfs

from .tree.message_tree import TreeCreator
from .mixins import ContentFunc, FileContentProvider, FileFunc, FileFuncSupported
from .types import InputSourceItem

T = TypeVar("T", bound=FileFuncSupported)


class FileFactory(
    FileFunc,
    ContentFunc,
    TreeCreator,
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
