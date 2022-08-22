from typing import Iterable, Mapping, Type

from telethon.tl.custom import Message

from .types import (
    Filter,
    FilterAllMessagesProto,
    FilterProviderProto,
    FilterSingleMessage,
)
from tgmount.util import col, func, compose_guards
from tgmount.tgclient.guards import document_or_photo_id
from tgmount.tgclient import guards


class ByTypes(FilterAllMessagesProto):

    guards = [
        guards.MessageWithCompressedPhoto,
        guards.MessageWithVideo,
        guards.MessageWithDocument,
        guards.MessageWithDocumentImage,
        guards.MessageWithVoice,
        guards.MessageWithKruzhochek,
        guards.MessageWithZip,
        guards.MessageWithMusic,
        guards.MessageWithAnimated,
        guards.MessageWithOtherDocument,
        guards.MessageWithSticker,
        guards.MessageWithVideoCompressed,
    ]

    guards_dict = {f.__name__: f.guard for f in guards}

    def __init__(
        self,
        types: list[FilterSingleMessage],
    ) -> None:
        self._types = types

    @staticmethod
    def from_config(gs: list[str]):
        return ByTypes(types=[ByTypes.guards_dict[g] for g in gs])

    async def filter(self, messages: Iterable[Message]):
        return list(
            filter(compose_guards(*self._types), messages),
        )


def from_guard(g: FilterSingleMessage):
    class FromGuard(FilterAllMessagesProto):
        def __init__(self, **kwargs) -> None:
            pass

        async def filter(self, messages: Iterable[Message]) -> list[Message]:
            print("FromGuard")
            return list(filter(g, messages))

        @staticmethod
        def from_config(gs):
            return FromGuard()

    return FromGuard


class OnlyUniqueDocs(FilterAllMessagesProto):
    PICKERS = {
        "last": lambda ms: ms[0],
        "first": lambda ms: ms[-1],
    }

    @staticmethod
    def from_config(d: dict):
        return OnlyUniqueDocs(picker=OnlyUniqueDocs.PICKERS[d["picker"]])

    def __init__(self, *, picker=PICKERS["first"]) -> None:
        self._picker = picker

    async def filter(self, messages: Iterable[Message]):
        result = []

        for k, v in func.group_by0(document_or_photo_id, messages).items():
            if len(v) > 1:
                result.append(self._picker(v))
            else:
                result.append(v[0])

        return result


class All(FilterAllMessagesProto):
    def __init__(self, **kwags) -> None:
        pass

    @staticmethod
    def from_config(d: dict):
        return All()

    async def filter(self, messages: Iterable[Message]) -> list[Message]:
        return list(messages)


class Last(FilterAllMessagesProto):
    def __init__(self, *, count: int) -> None:
        self._count = count

    @staticmethod
    def from_config(arg: int):
        return Last(count=arg)

    async def filter(self, messages: Iterable[Message]) -> list[Message]:
        return list(messages)[-self._count :]


class First(FilterAllMessagesProto):
    def __init__(self, *, count: int) -> None:
        self._count = count

    @staticmethod
    def from_config(arg: int):
        return Last(count=arg)

    async def filter(self, messages: Iterable[Message]) -> list[Message]:
        return list(messages)[: self._count]


class FilterProviderBase(FilterProviderProto):

    filters: Mapping[str, Type[Filter]]

    def get_filters(self) -> Mapping[str, Type[Filter]]:
        return self.filters
