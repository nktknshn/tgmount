from abc import abstractmethod
from typing import Mapping, Optional, Protocol, Type, Callable

from tgmount.config import ConfigError
from tgmount.util import none_fallback
from ..filters_types import (
    FilterFromConfigContext,
    FilterFromConfigProto,
    Filter,
    ParseFilter,
)

"""Taken filter name return `FilterFromConfigProto` class"""
FilterGetter = Callable[[str], Type[FilterFromConfigProto]]


class FilterProviderProto(Protocol):
    @abstractmethod
    def get(self, filter_name: str) -> Type[FilterFromConfigProto] | None:
        pass


class FilterProviderBase(FilterProviderProto):
    """ """

    filters: Mapping[str, Type[Filter]]
    filter_getters: list[FilterGetter]

    def __init__(
        self,
        # *,
        # filters: Mapping[str, Type[Filter]] | None = None,
        # taken
        # filter_getters: Optional[list[FilterGetter]] = None,
    ) -> None:
        pass
        # super().__init__()

    def append_filter_getter(self, fgetter: FilterGetter):
        self.filter_getters.append(fgetter)

    def get(self, key) -> Optional[Type[FilterFromConfigProto]]:
        _filter = self.filters.get(key)

        if _filter is not None:
            return _filter

        if len(self.filter_getters) == 0:
            return

        _fgs: list[Type[FilterFromConfigProto]] = []

        for fg in self.filter_getters:
            _fgs.append(fg(key))

        class _FromConfig(FilterFromConfigProto):
            @staticmethod
            def from_config(d, ctx: FilterFromConfigContext, parse_filter: ParseFilter):
                for fg in _fgs:
                    if _f := fg.from_config(d, ctx, parse_filter):
                        return _f
                raise ConfigError(f"Invalid filter: {key}")

        return _FromConfig
