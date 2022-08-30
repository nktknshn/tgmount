from abc import abstractmethod
from datetime import datetime
from typing import Callable, Mapping, Protocol, TypeGuard, TypeVar, cast

from telethon.tl.custom import Message
from tgmount import tgclient, vfs
from tgmount.tgclient import guards
from tgmount.util import compose_guards

# from .mixins import FileContentProvider, FileFunc, FileFuncSupported
from tgmount.tgclient.guards import *

from .types import FileContentProviderProto, FileFactoryProto, FilenameProviderProto


# def message_to_str(m: Message):
#     return f"Message(id={m.id}, file={m.file}, media={m.media}, document={m.document})"


# FileFuncSupported = (
#     MessageWithCompressedPhoto
#     | MessageWithVideo
#     | MessageWithDocument
#     | MessageWithDocumentImage
#     | MessageWithVoice
#     | MessageWithKruzhochek
#     | MessageWithZip
#     | MessageWithMusic
#     | MessageWithAnimated
#     | MessageWithOtherDocument
#     | MessageWithSticker
# )

# T = TypeVar("T", bound=FileFuncSupported)


# class FilenameProvider(FilenameProviderProto[FileFuncSupported]):
#     def filename(
#         self,
#         message: FileFuncSupported,
#     ) -> str:
#         if MessageWithCompressedPhoto.guard(message):
#             return f"{message.id}_photo.jpeg"
#         elif MessageWithVoice.guard(message):
#             return f"{message.id}_voice{message.file.ext}"
#         elif MessageWithSticker.guard(message):
#             return f"{message.id}_sticker_{message.file.name}"
#         elif MessageWithAnimated.guard(message):
#             return f"{message.id}_gif{message.file.ext}"
#         elif MessageWithKruzhochek.guard(message):
#             return f"{message.id}_circle{message.file.ext}"
#         elif MessageWithVideo.guard(message):
#             return f"{message.id}_video{message.file.ext}"
#         elif MessageWithMusic.guard(message):
#             return f"{message.id}_{message.file.name}"
#         elif MessageWithFilename.guard(message):
#             return f"{message.id}_{message.file.name}"

#         raise ValueError(f"incorret input message: {message_to_str(message)}")


# class FileFactoryMixin(
#     FilenameProvider,
#     FileContentProto,
#     FileFactoryProto[FileFuncSupported],
#     Protocol,
# ):
#     def supports(self, message: Message) -> TypeGuard[FileFuncSupported]:
#         return compose_guards(
#             MessageWithCompressedPhoto.guard,
#             MessageWithVideo.guard,
#             MessageWithFilename.guard,
#             MessageWithDocumentImage.guard,
#             MessageWithVoice.guard,
#             MessageWithKruzhochek.guard,
#             MessageWithZip.guard,
#             MessageWithMusic.guard,
#             MessageWithDocument.guard,
#             MessageWithOtherDocument.guard,
#             MessageWithAnimated.guard,
#             MessageWithSticker.guard,
#         )(message)

#     def file(self, message: FileFuncSupported, name=None) -> vfs.FileLike:

#         creation_time = getattr(message, "date", datetime.now())

#         return vfs.FileLike(
#             name if name is not None else self.filename(message),
#             content=self.file_content(message),
#             creation_time=creation_time,
#         )

#     def nfile(self, namef: Callable[[T], str]) -> Callable[[T], vfs.FileLike]:
#         return lambda message: self.file(message, namef(message))
