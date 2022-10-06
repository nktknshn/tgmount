from dataclasses import dataclass, field, replace
from typing import Callable, Mapping, TypeGuard, TypeVar

from tgmount import vfs

T = TypeVar("T")
R = TypeVar("R")


@dataclass
class MapTreeContext:
    path: list[str | int] = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    def push_path(self, element: str | int) -> "MapTreeContext":
        return replace(self, path=[*self.path, element])

    def put_extra(self, key: str, value) -> "MapTreeContext":
        return replace(self, extra={**self.extra, key: value})


TreeMapper = Callable[[MapTreeContext, T], R]


def map_tree(tree: vfs.Tree[T], mapper: TreeMapper[T, R], extra={}):
    context: MapTreeContext = MapTreeContext(extra=extra)
    return _map_tree(context, tree, mapper)


def map_value(tree_value: T, mapper: TreeMapper[T, R], extra={}):
    context: MapTreeContext = MapTreeContext(extra=extra)
    return mapper(
        context,
        tree_value,
    )


def _map_tree(
    context: MapTreeContext,
    tree: vfs.Tree[T],
    mapper: TreeMapper[T, R],
):
    # print(f"_walk_tree={list(tree.keys())}, path={context.path}")
    res = {}

    for k, tree_value in tree.items():
        ctx = context.push_path(k)

        if isinstance(tree_value, Mapping):
            res[k] = _map_tree(
                ctx,
                tree_value,
                mapper,
            )
        else:
            res[k] = mapper(
                ctx,
                tree_value,
            )

    return res


def is_tree(v) -> TypeGuard[vfs.Tree]:
    return isinstance(v, Mapping)
