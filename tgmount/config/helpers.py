import typing
from collections.abc import Callable, Mapping
from dataclasses import fields
from typing import Optional, Type, TypeGuard, TypeVar, Union

from tgmount.util import col
from .logger import logger

T = TypeVar("T")


def assert_that(pred, e):
    if not pred:
        raise e


def assert_not_none(pred: Optional[T], e) -> TypeGuard[T]:
    if pred is None:
        raise e
    return True


def _typecheck_union(
    value,
    typ,
):
    type_args = typing.get_args(typ)

    if type(value) is list:

        for arg in type_args:
            _type_origin = typing.get_origin(arg)

            if _type_origin is list:
                (_typ,) = typing.get_args(arg)
                for v in value:
                    if type(v) is not _typ:
                        return False

                return True

        return False

    else:
        typechekd = col.contains(type(value), type_args)

    return typechekd


def require(value: Optional[T], e) -> T:
    if value is None:
        raise e

    return value


def dict_get_value(
    d: Mapping,
    key: str,
    typ: Type[T],
    e: Exception,
    default=Optional[T],
) -> T:
    dv = d.get(key, default)
    dv = type_check(T, typ, e)

    return dv


def type_check(value, typ: Type[T], e) -> T:
    type_origin = typing.get_origin(typ)
    type_args = typing.get_args(typ)

    # if value is None:
    #     raise e

    if type_origin is Optional:
        if value is None:
            return None
        typechekd = typ is Optional[type(value)]
    elif type_origin is Union:
        typechekd = _typecheck_union(value, typ)
    else:
        typechekd = typ is type(value)

    if not typechekd:
        raise e

    return value


class ConfigError(Exception):
    pass


Loader = Callable[[dict], T]


def load_class_from_mapping(
    cls,
    d: Mapping,
    *,
    loaders: Optional[dict[str, Loader]] = None,
):
    logger.debug(f"load_class_from_dict({cls}, {d}, {loaders})")

    loaders = loaders if loaders is not None else {}

    assert_that(
        isinstance(d, Mapping),
        ConfigError(f"{d} is not dictionary"),
    )

    input_d = {}

    for field in fields(cls):
        if (loader := loaders.get(field.name)) is not None:
            input_d[field.name] = loader(d)
            continue

        value = d.get(field.name, field.default)

        type_check(
            value,
            field.type,
            ConfigError(
                f"Mismatching type for {field.name}. Expected: {field.type} received {type(value)}"
            ),
        )

        input_d[field.name] = value

    try:
        return cls(**input_d)
    except TypeError as e:
        raise ConfigError(f"Error loading {cls}: {e}")


def load_mapping(cls: Type | Callable, d: Mapping):
    def load_class(d):
        if hasattr(cls, "from_mapping"):
            return cls.from_mapping(d)

        if isinstance(cls, Type):
            return load_class_from_mapping(cls, d)

        return cls(d)

    return {k: load_class(v) for k, v in d.items()}


T = TypeVar("T")
R = TypeVar("R")

Tree = T | Mapping[str, "Tree[T]"]


def fold_tree(
    f: Callable[[T, R], R],
    tree: Tree[T],
    initial: R,
) -> R:
    res = initial
    if isinstance(tree, Mapping):
        for k, v in tree.items():
            if isinstance(v, Mapping):
                res = fold_tree(f, v, res)
            else:
                res = f(v, res)
    else:
        return f(tree, res)

    return res
