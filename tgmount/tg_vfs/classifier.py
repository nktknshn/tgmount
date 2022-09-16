from abc import abstractmethod
from collections.abc import Callable, Mapping
from typing import Any, Optional, Protocol, Type, TypeVar

from tgmount.tgclient import guards

I = TypeVar("I")
O = TypeVar("O")

classes = [
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
    guards.MessageWithText,
]

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
    | guards.MessageWithText
)


class ClassifierProto(Protocol[I, O]):
    @abstractmethod
    def classify(self, input_item: I) -> list[Type[O]]:
        ...

    @abstractmethod
    def try_get_guard(self, class_name: str) -> Optional[Callable[[Any], bool]]:
        ...


class ClassifierBase(ClassifierProto[Any, TelegramMessageClasses]):
    def __init__(self) -> None:
        pass

    @property
    def classes_dict(self) -> Mapping[str, TelegramMessageClasses]:
        return {k.__name__: k for k in classes}

    def is_class(self, input_item: Any):
        pass

    def try_get_guard(self, class_name: str) -> Optional[Callable[[Any], bool]]:
        if (klass := self.classes_dict.get(class_name)) is not None:
            return klass.guard

    def classify_str(self, input_item: Any) -> list[str]:
        return list(map(lambda k: k.__name__, self.classify(input_item)))

    def classify(self, input_item: Any) -> list[Type[TelegramMessageClasses]]:
        klasses: list[Type[TelegramMessageClasses]] = []

        for klass in classes:
            if klass.guard(input_item):
                klasses.append(klass)

        return klasses
