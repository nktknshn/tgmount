from typing import TypeVar, Mapping, Optional, Any

from tgmount import config
from tgmount.util import col
from .filters_types import FilterConfigValue, Filter
from .root_config_types import RootConfigContext
from .tgmount_types import TgmountResources
from .types import TgmountRootSource

T = TypeVar("T")


class RootProducerPropsReader:
    PROPS_KEYS = {"source", "filter", "cache", "wrappers", "producer", "treat_as"}

    def read_prop_source(self, d: TgmountRootSource) -> Mapping | None:
        source_prop_cfg = d.get("source")

        if source_prop_cfg is None:
            return

        if isinstance(source_prop_cfg, str):
            source_name = source_prop_cfg
            recursive = False
        else:
            source_name: str = source_prop_cfg["source"]
            recursive = source_prop_cfg.get("recursive", False)

        return dict(source_name=source_name, recursive=recursive)

    def read_prop_filter(self, d: TgmountRootSource) -> Mapping | None:
        filter_prop_cfg: FilterConfigValue = d.get("filter")

        if filter_prop_cfg is None:
            return

        filter_recursive = False

        if isinstance(filter_prop_cfg, dict) and "filter" in filter_prop_cfg:
            filter_recursive = filter_prop_cfg.get("recursive", False)
            filter_prop_cfg = filter_prop_cfg["filter"]

        if not isinstance(filter_prop_cfg, list):
            filter_prop_cfg = [filter_prop_cfg]

        filter_prop_cfg = to_list_of_single_key_dicts(filter_prop_cfg)

        filters = []

        for f_item in filter_prop_cfg:
            if isinstance(f_item, str):
                f_name = f_item
                filter_arg = None
            else:
                f_name, filter_arg = col.get_first_pair(f_item)

            filters.append((f_name, filter_arg))

        return dict(filters=filters, recursive=filter_recursive)

    def read_prop_cache(self, d: TgmountRootSource):
        _cache = d.get("cache")

        if _cache is None:
            return

        return _cache

    def read_prop_wrappers(
        self, d: TgmountRootSource
    ) -> Optional[list[tuple[str, Any | None]]]:
        _wrappers = d.get("wrappers")

        if _wrappers is None:
            return

        if not isinstance(_wrappers, list):
            _wrappers = [_wrappers]

        wrappers = []

        for w_item in _wrappers:
            if isinstance(w_item, str):
                wrapper_name = w_item
                wrapper_arg = None
            else:
                wrapper_name, wrapper_arg = col.get_first_pair(w_item)

            wrappers.append((wrapper_name, wrapper_arg))

        return wrappers

    def read_prop_producer(self, d: TgmountRootSource) -> tuple[str, Any] | None:
        _producer_dict = d.get("producer")

        if _producer_dict is None:
            return

        if isinstance(_producer_dict, str):
            _producer_dict = {_producer_dict: {}}

        producer_name = col.get_first_key(_producer_dict)

        if producer_name is None:
            raise config.ConfigError(f"Invalid producer definition: {_producer_dict}")

        producer_arg = _producer_dict[producer_name]

        return producer_name, producer_arg

    def get_filters_from_prop(
        self, filter_prop: list, resources: TgmountResources, ctx: RootConfigContext
    ) -> list[Filter]:
        def _parse_filter(filt: FilterConfigValue) -> list[Filter]:
            filter_prop = self.read_prop_filter({"filter": filt})
            if filter_prop is None:
                return []
            return self.get_filters_from_prop(filter_prop["filters"], resources, ctx)

        filters = []
        for f_name, f_arg in filter_prop:
            filter_cls = resources.filters.get(f_name)

            if filter_cls is None:
                raise config.ConfigError(
                    f"missing filter: {f_name} in {ctx.current_path}"
                )

            _filter = filter_cls.from_config(f_arg, ctx, _parse_filter)

            filters.append(_filter)

        return filters


def to_list_of_single_key_dicts(
    items: list[str | dict[str, dict]]
) -> list[str | dict[str, dict]]:
    res = []

    for item in items:
        if isinstance(item, str):
            res.append(item)
        else:
            res.extend(dict([t]) for t in item.items())

    return res
