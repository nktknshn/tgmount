from abc import abstractmethod
from typing import Any, Iterable, Optional, Protocol, Type, TypeVar, Callable

from telethon.tl.custom import Message

from tgmount.tgclient import guards
from tgmount.tgclient.guards import MessageDownloadable
from tgmount.util import col, func
from tgmount.util.guards import compose_try_gets
from .filters_types import (
    FilterConfigValue,
    FilterFromConfigContext,
    InstanceFromConfigProto,
    FilterFromConfigProto,
    FilterAllMessagesProto,
    FilterSingleMessage,
    Filter,
    ParseFilter,
)
from .types import Set

T = TypeVar("T")


def from_function(
    func: Callable[
        [Any, FilterFromConfigContext, "ParseFilter"],
        Optional["FilterAllMessagesProto"],
    ]
) -> Type["FilterFromConfigProto"]:
    class FilterFromConfig(FilterFromConfigProto):
        @staticmethod
        def from_config(
            d: Any, ctx: FilterFromConfigContext, parse_filter: ParseFilter
        ) -> Optional[Filter]:
            return func(d, ctx, parse_filter)

    return FilterFromConfig


class ByTypes(FilterAllMessagesProto):

    # guards: list[Type[TryGetMethodProto]] = []
    #  = SupportsMethod.supported

    def __init__(
        self,
        filter_types: list[FilterSingleMessage],
    ) -> None:
        self._filter_types = filter_types

    @staticmethod
    def from_config(
        gs: list[str], ctx: FilterFromConfigContext, parse_filter: ParseFilter
    ):
        return ByTypes(
            filter_types=[ctx.file_factory.try_get_dict[g] for g in gs],
        )

    async def filter(self, messages: Iterable[Message]):
        return list(
            filter(compose_try_gets(*self._filter_types), messages),
        )


from .logger import logger as _logger

logger = _logger.getChild("filters")


class OnlyUniqueDocs(FilterAllMessagesProto):
    logger = logger.getChild("OnlyUniqueDocs")

    PICKERS = {
        "last": lambda ms: ms[-1],
        "first": lambda ms: ms[0],
    }

    @staticmethod
    def from_config(
        d: Optional[dict], ctx: FilterFromConfigContext, parse_filter: ParseFilter
    ):
        if d is not None:
            return OnlyUniqueDocs(picker=OnlyUniqueDocs.PICKERS[d["picker"]])
        else:
            return OnlyUniqueDocs()

    def __init__(self, *, picker=PICKERS["first"]) -> None:
        self._picker = picker

    async def filter(self, messages: Iterable[MessageDownloadable]):
        result = []

        non_downloadable = filter(lambda m: not MessageDownloadable.guard(m), messages)

        self.logger.debug(f"filtering... {messages}")

        for k, v in func.group_by0(
            MessageDownloadable.document_or_photo_id,
            filter(MessageDownloadable.guard, messages),
        ).items():
            if len(v) > 1:
                picked = self._picker(list(sorted(v, key=lambda v: v.id)))
                self.logger.debug(f"duplicate: {v}, picked: {picked}")
                result.append(picked)
            else:
                result.append(v[0])

        return [*result, *non_downloadable]


class ByExtension(FilterAllMessagesProto):
    logger = logger.getChild("ByExtension")

    def __init__(self, ext: str) -> None:
        self.ext = ext

    @staticmethod
    def from_config(ext: str, ctx: FilterFromConfigContext, parse_filter: ParseFilter):
        return ByExtension(ext)

    async def filter(self, messages: Iterable[Message]) -> list[Message]:
        self.logger.debug(f"filtering {messages} by extension {self.ext}")
        res = [
            m
            for m in filter(guards.MessageWithFilename.guard, messages)
            if m.file.ext == self.ext
        ]
        self.logger.debug(f"result={res}")
        return res


class Not(FilterAllMessagesProto):
    def __init__(self, filters: list[Filter]) -> None:
        self.filters = filters

    @staticmethod
    def from_config(
        _filter: FilterConfigValue,
        ctx: FilterFromConfigContext,
        parse_filter: ParseFilter,
    ):
        return Not(parse_filter(_filter))

    async def filter(self, messages: Iterable[Message]) -> list[Message]:
        _ms = Set(messages)

        for f in self.filters:
            _ms = await f.filter(_ms)

        return [m for m in messages if not m in _ms]


class Union(FilterAllMessagesProto):
    def __init__(self, filters: list[Filter]) -> None:
        self.filters = filters

    @staticmethod
    def from_config(
        gs: FilterConfigValue, ctx: FilterFromConfigContext, parse_filter: ParseFilter
    ):
        return Union(filters=parse_filter(gs))

    async def filter(self, messages: Iterable[Message]):
        _ms = []
        for f in self.filters:
            _ms.extend(await f.filter(messages))

        return await OnlyUniqueDocs().filter(_ms)


class And(FilterAllMessagesProto):
    def __init__(self, filters: list[Filter]) -> None:
        self.filters = filters

    @staticmethod
    def from_config(
        gs: FilterConfigValue, ctx: FilterFromConfigContext, parse_filter: ParseFilter
    ):
        return And(filters=parse_filter(gs))

    async def filter(self, messages: Iterable[Message]):

        if len(self.filters) == 0:
            return messages

        _ms = await self.filters[0].filter(messages)

        for f in self.filters[1:]:
            _ = await f.filter(messages)
            _ms = list(filter(lambda m: col.contains(m, _), _ms))

        return await OnlyUniqueDocs().filter(_ms)


class Seq(FilterAllMessagesProto):
    def __init__(self, filters: list[Filter]) -> None:
        self.filters = filters

    @staticmethod
    def from_config(
        gs: FilterConfigValue, ctx: FilterFromConfigContext, parse_filter: ParseFilter
    ):
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
    def from_config(d: dict, ctx: FilterFromConfigContext, parse_filter: ParseFilter):
        return All()

    async def filter(self, messages: Iterable[Message]) -> list[Message]:
        return list(messages)


class Last(FilterAllMessagesProto):
    def __init__(self, *, count: int) -> None:
        self._count = count

    @staticmethod
    def from_config(arg: int, ctx: FilterFromConfigContext, parse_filter: ParseFilter):
        return Last(count=arg)

    async def filter(self, messages: Iterable[Message]) -> list[Message]:
        return list(messages)[-self._count :]


class First(FilterAllMessagesProto):
    def __init__(self, *, count: int) -> None:
        self._count = count

    @staticmethod
    def from_config(arg: int, ctx: FilterFromConfigContext, parse_filter: ParseFilter):
        return Last(count=arg)

    async def filter(self, messages: Iterable[Message]) -> list[Message]:
        return list(messages)[: self._count]


# def from_try_get(g: TryGetFunc) -> Type[Filter]:
#     class FromTryGet(FilterAllMessagesProto):
#         def __init__(self, **kwargs) -> None:
#             pass

#         async def filter(self, messages: Iterable[Message]) -> list[Message]:
#             return list(filter(lambda m: g(m) is not None, messages))

#         @staticmethod
#         def from_config(gs, ctx: FilterFromConfigContext, parse_filter: ParseFilter):
#             return FromTryGet()

#     return FromTryGet


def from_guard(g: Callable[[Any], bool]) -> Type[Filter]:
    class FromGuardFunc(FilterAllMessagesProto):
        def __init__(self, **kwargs) -> None:
            pass

        async def filter(self, messages: Iterable[Message]) -> list[Message]:
            return list(filter(lambda m: g(m), messages))

        @staticmethod
        def from_config(gs, ctx: FilterFromConfigContext, parse_filter: ParseFilter):
            return FromGuardFunc()

    return FromGuardFunc


def from_context_classifier(klass_name: str) -> Type[FilterFromConfigProto]:
    """If `file_factory` supports mounting message of `filter_name` type returns filter for that type, otherwise returns `None`"""

    def from_config(
        d, ctx: FilterFromConfigContext, parse_filter: ParseFilter
    ) -> Optional[Filter]:

        func = ctx.classifier.try_get_guard(klass_name)

        if func is not None:
            return from_guard(func).from_config(d, ctx, parse_filter)

    return from_function(from_config)


class ProviderMappingProto(Protocol[T]):
    @abstractmethod
    def get(self, key) -> Optional[Type[InstanceFromConfigProto[T]]]:
        ...
