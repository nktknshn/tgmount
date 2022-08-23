from collections.abc import Callable
from typing import Iterable, Mapping, Type

from telethon.tl.custom import Message

from tgmount.tg_vfs.file_factory import SupportsMethod

from .types import (
    Filter,
    FilterAllMessagesProto,
    FilterProviderProto,
    FilterSingleMessage,
)
from tgmount.util import col, func, compose_guards
from tgmount.tgclient.guards import document_or_photo_id
from tgmount.tgclient import guards


FilterDict = str | dict[str, dict] | list[str | dict[str, dict]]
ParseFilter = Callable[[FilterDict], list[Filter]]


class ByTypes(FilterAllMessagesProto):

    guards = SupportsMethod.supported

    guards_dict = {f.__name__: f.guard for f in guards}

    def __init__(
        self,
        types: list[FilterSingleMessage],
    ) -> None:
        self._types = types

    @staticmethod
    def from_config(gs: list[str], parse_filter: ParseFilter):
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
            return list(filter(g, messages))

        @staticmethod
        def from_config(gs, parse_filter: ParseFilter):
            return FromGuard()

    return FromGuard


class OnlyUniqueDocs(FilterAllMessagesProto):
    PICKERS = {
        "last": lambda ms: ms[0],
        "first": lambda ms: ms[-1],
    }

    @staticmethod
    def from_config(d: dict, parse_filter: ParseFilter):
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


class ByExtension(FilterAllMessagesProto):
    def __init__(self, ext: str) -> None:
        self.ext = ext

    @staticmethod
    def from_config(ext: str, parse_filter: ParseFilter):
        return ByExtension(ext)

    async def filter(self, messages: Iterable[Message]) -> list[Message]:
        return [
            m
            for m in filter(guards.MessageWithFilename.guard, messages)
            if m.file.ext == self.ext
        ]


class Not(FilterAllMessagesProto):
    def __init__(self, filters: list[Filter]) -> None:
        self.filters = filters

    @staticmethod
    def from_config(_filter: FilterDict, parse_filter: ParseFilter):
        return Not(parse_filter(_filter))

    async def filter(self, messages: Iterable[Message]) -> list[Message]:
        _ms = list(messages)
        for f in self.filters:
            _ms = await f.filter(_ms)

        return [m for m in messages if not col.contains(m, _ms)]


class Union(FilterAllMessagesProto):
    def __init__(self, filters: list[Filter]) -> None:
        self.filters = filters

    @staticmethod
    def from_config(gs: FilterDict, parse_filter: ParseFilter):
        return Union(filters=parse_filter(gs))

    async def filter(self, messages: Iterable[Message]):
        _ms = []
        for f in self.filters:
            _ms.extend(await f.filter(messages))

        return await OnlyUniqueDocs().filter(_ms)


class Seq(FilterAllMessagesProto):
    def __init__(self, filters: list[Filter]) -> None:
        self.filters = filters

    @staticmethod
    def from_config(gs: FilterDict, parse_filter: ParseFilter):
        return Seq(filters=parse_filter(gs))

    async def filter(self, messages: Iterable[Message]):
        messages = list(messages)
        for f in self.filters:
            messages = await f.filter(messages)

        return messages


class All(FilterAllMessagesProto):
    def __init__(self, **kwags) -> None:
        pass

    @staticmethod
    def from_config(d: dict, parse_filter: ParseFilter):
        return All()

    async def filter(self, messages: Iterable[Message]) -> list[Message]:
        return list(messages)


class Last(FilterAllMessagesProto):
    def __init__(self, *, count: int) -> None:
        self._count = count

    @staticmethod
    def from_config(arg: int, parse_filter: ParseFilter):
        return Last(count=arg)

    async def filter(self, messages: Iterable[Message]) -> list[Message]:
        return list(messages)[-self._count :]


class First(FilterAllMessagesProto):
    def __init__(self, *, count: int) -> None:
        self._count = count

    @staticmethod
    def from_config(arg: int, parse_filter: ParseFilter):
        return Last(count=arg)

    async def filter(self, messages: Iterable[Message]) -> list[Message]:
        return list(messages)[: self._count]


class FilterProviderBase(FilterProviderProto):

    filters: Mapping[str, Type[Filter]]

    def get_filters(self) -> Mapping[str, Type[Filter]]:
        return self.filters
