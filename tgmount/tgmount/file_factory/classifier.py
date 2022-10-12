from typing import Generic, TypeVar
from .classifierbase import ClassifierBase
from tgmount.tgclient import guards

TelegramMessageClasses = (
    guards.TelegramMessage
    | guards.MessageDownloadable
    | guards.MessageForwarded
    | guards.MessageWithAnimated
    | guards.MessageWithAudio
    | guards.MessageWithVoice
    | guards.MessageWithCompressedPhoto
    | guards.MessageWithDocument
    | guards.MessageWithDocumentImage
    | guards.MessageWithFilename
    | guards.MessageWithKruzhochek
    | guards.MessageWithMusic
    | guards.MessageWithOtherDocument
    | guards.MessageWithZip
    | guards.MessageWithVideoFile
    | guards.MessageWithVideo
    | guards.MessageWithSticker
    # | guards.MessageWithText
    | guards.MessageWithReactions
    | guards.MessageWithoutDocument
)

T = TypeVar("T", bound=guards.ClassWithGuard)


class ClassifierDefault(ClassifierBase[TelegramMessageClasses | T], Generic[T]):
    classes: list[TelegramMessageClasses | T] = [
        guards.TelegramMessage,
        guards.MessageDownloadable,
        guards.MessageForwarded,
        guards.MessageWithAnimated,
        guards.MessageWithVoice,
        guards.MessageWithAudio,
        guards.MessageWithCompressedPhoto,
        guards.MessageWithDocument,
        guards.MessageWithDocumentImage,
        guards.MessageWithFilename,
        guards.MessageWithKruzhochek,
        guards.MessageWithMusic,
        guards.MessageWithOtherDocument,
        guards.MessageWithZip,
        guards.MessageWithVideoFile,
        guards.MessageWithVideo,
        guards.MessageWithSticker,
        # guards.MessageWithText,
        guards.MessageWithReactions,
        guards.MessageWithoutDocument,
    ]
