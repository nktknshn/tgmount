from typing import Awaitable, Callable, Iterable, Mapping, Optional, TypeVar


fst = lambda a: a[0]
snd = lambda a: a[1]

_T1 = TypeVar("_T1")
_T2 = TypeVar("_T2")


_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


def map_values(func: Callable[[_T1], _T2], d: Mapping[_KT, _T1]) -> Mapping[_KT, _T2]:
    return {k: func(v) for k, v in d.items()}


def group_by0(
    f: Callable[[_VT], _KT],
    items: Iterable[_VT],
) -> dict[_KT, list[_VT]]:
    res: dict[_KT, list[_VT]] = {}

    for a in items:
        k = f(a)
        if k not in res:
            res[k] = []

        res[k].append(a)

    return res


def strip_minimum(
    d: dict[Optional[_KT], Iterable[_VT]], minimum: int
) -> tuple[dict[Optional[_KT], list[_VT]], list[_VT]]:
    result = []
    less = []

    for k, v in d.items():
        if len(list(v)) < minimum:
            less.extend(v)
        else:
            result.append((k, v))

    return dict(result), less


async def group_by_func_async(
    func: Callable[[_VT], Awaitable[_KT | None]], items: Iterable[_VT], minimum=1
) -> tuple[dict[_KT, list[_VT]], list[_VT], list[_VT],]:

    res: list[tuple[Optional[_KT], _VT]] = []

    for m in items:
        key = await func(m)

        res.append((key, m))

    d = group_by0(fst, res)
    d = {k: list(map(snd, v)) for k, v in d.items()}

    if None in d:
        nones = d[None]
        del d[None]
    else:
        nones = []

    if minimum > 1:
        return (*strip_minimum(d, minimum), nones)

    return (d, [], nones)
