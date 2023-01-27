import random
from typing import Any, Callable, Optional, Type, TypeGuard, TypeVar, overload

import pathvalidate

from .col import find, sets_difference, dict_exclude
from .guards import compose_guards

T = TypeVar("T")
O = TypeVar("O")


@overload
def yes(value: Optional[T]) -> TypeGuard[T]:
    ...


@overload
def yes(value: Optional[Any], typ: Type[O]) -> TypeGuard[O]:
    ...


def yes(value: Optional[T], typ: Optional[Type[O]] = None) -> TypeGuard[O | T]:

    if typ is None:
        return value is not None

    if value is not None and isinstance(value, typ):
        return True
    elif value is None:
        return False
    else:
        raise ValueError(f"'{value}' is not '{typ}'")


def none_fallback(value: Optional[T], default: T) -> T:
    return value if value is not None else default


def map_none(value: Optional[T], func: Callable[[T], O]) -> O | None:
    return func(value) if value is not None else None


def map_none_else(value: Optional[T], func: Callable[[T], O], default: O) -> O:

    return none_fallback(map_none(value, func), default)


def none_fallback_lazy(value: Optional[T], default: Callable[[], T]) -> T:
    return value if value is not None else default()


def is_not_none(value: Optional[T]) -> TypeGuard[T]:
    return value is not None


def int_or_string(value: int | str):
    try:
        return int(value)
    except ValueError:
        return str(value)


def sanitize_string_for_path(name: str) -> str:
    name = name.replace("/", "")

    if len(name) > 0 and name[0] == "-":
        name = "_" + name[1:]

    return name


import time
from functools import wraps


def measure_time(*, logger_func, threshold=None):
    def measure_time(func):
        @wraps(func)
        async def inner_function(*args, **kwargs):
            started = time.time_ns()
            res = await func(*args, **kwargs)
            duration = time.time_ns() - started
            duration = duration / 1000 / 1000

            if threshold is not None and duration < threshold:
                return res

            logger_func(f"{func} = {int(duration)} ms")

            return res

        return inner_function

    return measure_time


random_int = lambda max: lambda: int(max * random.random())
