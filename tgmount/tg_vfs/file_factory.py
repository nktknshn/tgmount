from abc import abstractmethod
from datetime import datetime
from typing import Callable, Protocol, TypeGuard, TypeVar

from telethon.tl.custom import Message
from tgmount import vfs
from tgmount.tgclient.guards import *
from tgmount.tgclient.files_source import get_downloadable_item

from tgmount.util import compose_guards

from .tree.message_tree import TreeCreator
from .types import FileContentProto, FileFactoryProto

T = TypeVar("T")

FileFuncSupported = (
    MessageWithCompressedPhoto
    | MessageWithVideo
    | MessageWithDocumentImage
    | MessageWithVoice
    | MessageWithKruzhochek
    | MessageWithZip
    | MessageWithMusic
    | MessageWithDocument
    | MessageWithOtherDocument
    | MessageWithAnimated
    | MessageWithSticker
)


class SupportsMethod:
    supported = [
        # MessageWithFilename,
        MessageWithMusic,
        MessageWithVoice,
        MessageWithSticker,
        MessageWithAnimated,
        MessageWithKruzhochek,
        MessageWithCompressedPhoto,
        MessageWithDocumentImage,
        MessageWithVideoFile,
        MessageWithVideo,
        MessageWithZip,
        MessageWithOtherDocument,
    ]

    def supports(self, message: Message) -> TypeGuard[FileFuncSupported]:
        return compose_guards(*[t.guard for t in self.supported])(message)

    def message_type(self, message: Message) -> Optional[str]:
        ts = self.message_types(message)
        if len(ts) > 0:
            return ts[0]

    def message_types(self, message: Message) -> list[str]:
        ts = []
        for t in self.supported:
            if t.guard(message):
                ts.append(t.__name__)
        return ts


class FilenameMethod(SupportsMethod):
    def size(
        self,
        message: FileFuncSupported,
    ) -> int:
        return get_downloadable_item(message).size

    def filename(
        self,
        message: FileFuncSupported,
    ) -> str:
        if MessageWithCompressedPhoto.guard(message):
            return f"{message.id}_photo.jpeg"
        elif MessageWithVoice.guard(message):
            return f"{message.id}_voice{message.file.ext}"
        elif MessageWithSticker.guard(message):
            return f"{message.id}_{message.file.name}"
        elif MessageWithAnimated.guard(message):
            if message.file.name:
                return f"{message.id}_{message.file.name}"
            else:
                return f"{message.id}_gif{message.file.ext}"
        elif MessageWithKruzhochek.guard(message):
            return f"{message.id}_circle{message.file.ext}"
        elif MessageWithVideoFile.guard(message):
            if message.file.name is not None:
                return f"{message.id}_{message.file.name}"
            else:
                return f"{message.id}_video{message.file.ext}"
        elif MessageWithVideo.guard(message):
            return f"{message.id}_video{message.file.ext}"
        elif MessageWithMusic.guard(message):
            if message.file.name:
                return f"{message.id}_{message.file.name}"
            else:
                return f"{message.id}_music{message.file.ext}"
        elif MessageWithFilename.guard(message):
            return f"{message.id}_{message.file.name}"

        raise ValueError(f"incorret input message: {message_to_str(message)}")


class FactoryMethod(FilenameMethod):
    files_source: FileContentProto

    def file_content(self, message: MessageDownloadable) -> vfs.FileContent:
        return self.files_source.file_content(message)

    def file(self, message: FileFuncSupported, name=None) -> vfs.FileLike:

        creation_time = getattr(message, "date", datetime.now())

        return vfs.FileLike(
            name if name is not None else self.filename(message),
            content=self.file_content(message),
            creation_time=creation_time,
        )

    def nfile(
        self, namef: Callable[[FileFuncSupported], str]
    ) -> Callable[[FileFuncSupported], vfs.FileLike]:
        return lambda message: self.file(message, namef(message))


class FileFactory(
    FactoryMethod,
    TreeCreator,
    FileFactoryProto[FileFuncSupported],
):
    def __init__(self, files_source: FileContentProto) -> None:
        self.files_source = files_source


def message_to_str(m: Message):
    return f"Message(id={m.id}, file={m.file}, media={m.media}, document={m.document})"
