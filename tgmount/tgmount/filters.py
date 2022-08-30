from abc import abstractmethod, abstractstaticmethod
from collections.abc import Callable
from typing import Any, Iterable, Mapping, Optional, Protocol, Type, TypeGuard, TypeVar

from telethon.tl.custom import Message
from tgmount import tg_vfs
from tgmount.config import ConfigError
from tgmount.tg_vfs.file_factory import SupportsMethodBase, TryGetFunc
from tgmount.tgclient import guards
from tgmount.tgclient.guards import MessageDownloadable
from tgmount.util import col, compose_guards, func, none_fallback
from tgmount.util.guards import compose_try_gets

T = TypeVar("T")

FilterConfigValue = str | dict[str, dict] | list[str | dict[str, dict]]


class FilterFromConfigContext(Protocol):
    file_factory: SupportsMethodBase
    classifier: tg_vfs.ClassifierBase


class InstanceFromConfigProto(Protocol[T]):
    @abstractstaticmethod
    def from_config(*args) -> Optional[T]:
        ...


class FilterFromConfigProto(InstanceFromConfigProto["FilterAllMessagesProto"]):
    @abstractstaticmethod
    def from_config(*args) -> Optional["FilterAllMessagesProto"]:
        ...


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


class FilterAllMessagesProto(Protocol):
    @abstractmethod
    def __init__(self, **kwargs) -> None:
        pass

    @abstractmethod
    async def filter(self, messages: Iterable[Message]) -> list[Message]:
        ...

    @abstractstaticmethod
    def from_config(*args) -> "FilterAllMessagesProto":
        ...


FilterSingleMessage = Callable[[Message], T | None]
FilterAllMessages = FilterAllMessagesProto

Filter = FilterAllMessages
ParseFilter = Callable[[FilterConfigValue], list[Filter]]


class FilterProviderProto(Protocol):
    @abstractmethod
    def get_filters(self) -> Mapping[str, Type[Filter]]:
        pass


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


class OnlyUniqueDocs(FilterAllMessagesProto):
    PICKERS = {
        "last": lambda ms: ms[0],
        "first": lambda ms: ms[-1],
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

        for k, v in func.group_by0(
            MessageDownloadable.document_or_photo_id,
            filter(MessageDownloadable.guard, messages),
        ).items():
            if len(v) > 1:
                result.append(self._picker(v))
            else:
                result.append(v[0])

        return [*result, *non_downloadable]


class ByExtension(FilterAllMessagesProto):
    def __init__(self, ext: str) -> None:
        self.ext = ext

    @staticmethod
    def from_config(ext: str, ctx: FilterFromConfigContext, parse_filter: ParseFilter):
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
    def from_config(
        _filter: FilterConfigValue,
        ctx: FilterFromConfigContext,
        parse_filter: ParseFilter,
    ):
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


"""Taken filter name return `FilterFromConfigProto` class"""
FilterGetter = Callable[[str], Type[FilterFromConfigProto]]


class FiltersMapping:
    def __init__(
        self,
        *,
        filters: Mapping[str, Type[Filter]] = {},
        # taken
        filter_getters: Optional[list[FilterGetter]] = None,
    ) -> None:
        super().__init__()
        self._filters: Mapping[str, Type[Filter]] = filters
        self._filter_getters = none_fallback(filter_getters, [])

    def append_filter_getter(self, fgetter: FilterGetter):
        self._filter_getters.append(fgetter)

    def get(self, key) -> Optional[Type[FilterFromConfigProto]]:
        _filter = self._filters.get(key)

        if _filter is not None:
            return _filter

        if len(self._filter_getters) == 0:
            return

        _fgs: list[Type[FilterFromConfigProto]] = []

        for fg in self._filter_getters:
            _fgs.append(fg(key))

        class _FromConfig(FilterFromConfigProto):
            @staticmethod
            def from_config(d, ctx: FilterFromConfigContext, parse_filter: ParseFilter):
                for fg in _fgs:
                    if _f := fg.from_config(d, ctx, parse_filter):
                        return _f
                raise ConfigError(f"Invalid filter: {key}")

        return _FromConfig


class FilterProviderBase(FilterProviderProto):

    filters: FiltersMapping = FiltersMapping()

    def get_filters(self) -> FiltersMapping:
        return self.filters
