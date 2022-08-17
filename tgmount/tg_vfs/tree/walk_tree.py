from typing import Callable, Iterable, Mapping, Protocol, TypedDict, TypeGuard, TypeVar

from telethon.tl.custom import Message
from tgmount import vfs

from ..tree.types import WalkTreeContext

T = TypeVar("T")
R = TypeVar("R")

# WalkTreeContext = TypedDict("WalkTreeContext", path=list[str | int], extra=dict)
Mapper = Callable[[WalkTreeContext, T], R]


def walk_tree(tree: vfs.Tree[T], mapper: Mapper[T, R], extra={}):
    context: WalkTreeContext = WalkTreeContext(extra=extra)
    return _walk_tree(context, tree, mapper)


def walk_value(tree_value: T, mapper: Mapper[T, R], extra={}):
    context: WalkTreeContext = WalkTreeContext(extra=extra)
    return mapper(
        context,
        tree_value,
    )


def _walk_tree(
    context: WalkTreeContext,
    tree: vfs.Tree[T],
    mapper: Mapper[T, R],
):
    # print(f"_walk_tree={list(tree.keys())}, path={context.path}")
    res = {}

    for k, tree_value in tree.items():
        ctx = context.push_path(k)

        if isinstance(tree_value, Mapping):
            res[k] = _walk_tree(
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
