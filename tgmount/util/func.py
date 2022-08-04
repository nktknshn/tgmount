from typing import Callable, Iterable, TypeVar
import funcy as funcy
import functools

cmap = funcy.curry(map)
compose = funcy.compose
group_by = funcy.group_by
walk_values = funcy.walk_values
fst = lambda a: a[0]
endswith = funcy.partial(funcy.rpartial, str.endswith)

_T1 = TypeVar("_T1")
_T2 = TypeVar("_T2")


list_map: Callable[[Callable[[_T1], _T2], Iterable[_T1]], list[_T2]] = compose(
    list, map
)

set_map = compose(set, map)
list_filter = compose(list, filter)
