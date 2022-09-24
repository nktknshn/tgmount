# from collections.abc import Mapping
# from datetime import datetime
# from typing import Callable, ClassVar, Protocol, TypeGuard, TypeVar

# from telethon.tl.custom import Message
# from tgmount import vfs
# from tgmount.tgclient.guards import *

# from .error import FileFactoryError
# from .types import FileContentProviderProto

# T = TypeVar("T")

# TryGetFunc = Callable[[Message], Optional[T]]


# class SupportsMethodBase(Protocol[T]):
#     supported: ClassVar[list[Type[WithTryGetMethodProto]]]

#     @property
#     def try_get_dict(self) -> Mapping[str, Type[TryGetFunc]]:
#         return {f.__name__: f.try_get for f in self.supported}

#     def try_get(self, message: Message) -> Optional[T]:
#         for t in self.supported:
#             if (m := t.try_get(message)) is not None:
#                 return m

#     def supports(self, message: Message) -> TypeGuard[T]:
#         return self.try_get(message) is not None
#         # return compose_guards(*[t.try_get for t in self.supported])(message)

#     def message_type(self, message: Message) -> Optional[str]:
#         ts = self.message_types(message)
#         if len(ts) > 0:
#             return ts[0]

#     def message_types(self, message: Message) -> list[str]:
#         ts = []
#         for t in self.supported:
#             if bool(t.try_get(message)):
#                 ts.append(t.__name__)
#         return ts


# FileFactorySupportedTypes = (
#     MessageWithMusic
#     | MessageWithVoice
#     | MessageWithSticker
#     | MessageWithAnimated
#     | MessageWithKruzhochek
#     | MessageWithCompressedPhoto
#     | MessageWithDocumentImage
#     | MessageWithVideoFile
#     | MessageWithVideo
#     | MessageWithZip
#     | MessageWithOtherDocument
# )


# class SupportsMethod(SupportsMethodBase[FileFactorySupportedTypes]):

#     supported = [
#         MessageWithMusic,
#         MessageWithVoice,
#         MessageWithSticker,
#         MessageWithAnimated,
#         MessageWithKruzhochek,
#         MessageWithCompressedPhoto,
#         MessageWithDocumentImage,
#         MessageWithVideoFile,
#         MessageWithVideo,
#         MessageWithZip,
#         MessageWithOtherDocument,
#     ]


# class FilenameMethod:
#     def filename(
#         self,
#         message: FileFactorySupportedTypes,
#     ) -> str:
#         if MessageWithCompressedPhoto.guard(message):
#             return f"{message.id}_photo.jpeg"
#         elif MessageWithVoice.guard(message):
#             return f"{message.id}_voice{message.file.ext}"
#         elif MessageWithSticker.guard(message):
#             return f"{message.id}_{message.file.name}"
#         elif MessageWithAnimated.guard(message):
#             if message.file.name:
#                 return f"{message.id}_{message.file.name}"
#             else:
#                 return f"{message.id}_gif{message.file.ext}"
#         elif MessageWithKruzhochek.guard(message):
#             return f"{message.id}_circle{message.file.ext}"
#         elif MessageWithVideoFile.guard(message):
#             if message.file.name is not None:
#                 return f"{message.id}_{message.file.name}"
#             else:
#                 return f"{message.id}_video{message.file.ext}"
#         elif MessageWithVideo.guard(message):
#             return f"{message.id}_video{message.file.ext}"
#         elif MessageWithMusic.guard(message):
#             if message.file.name:
#                 return f"{message.id}_{message.file.name}"
#             else:
#                 return f"{message.id}_music{message.file.ext}"
#         elif MessageWithFilename.guard(message):
#             return f"{message.id}_{message.file.name}"

#         raise ValueError(f"incorret input message: {message_to_str(message)}")


# class FactoryMethod(FilenameMethod):
#     files_source: FileContentProviderProto

#     def size(self, message: Message) -> int:
#         return self.file_content(message).size

#     def file_content(self, message: Message) -> vfs.FileContent:
#         if MessageDownloadable.guard(message):
#             return self.files_source.file_content(message)

#         raise FileFactoryError(f"Cannot get file content for {message}.")

#     def file(self, message: FileFactorySupportedTypes, name=None) -> vfs.FileLike:

#         creation_time = getattr(message, "date", datetime.now())

#         return vfs.FileLike(
#             name if name is not None else self.filename(message),
#             content=self.file_content(message),
#             creation_time=creation_time,
#         )


# def message_to_str(m: Message):
#     return f"Message(id={m.id}, file={m.file}, media={m.media}, document={m.document})"
