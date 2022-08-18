from dataclasses import dataclass, fields
from typing import Optional, Union
import typing
from tgmount.util import col
from tgmount import vfs


def assert_that(pred, e):
    if not pred:
        raise e


class ConfigError(Exception):
    pass


def load_class_from_dict(cls, d: dict):
    assert_that(
        isinstance(d, dict),
        ConfigError(f"{d} is not dictionary"),
    )

    for field in fields(cls):
        optional = field.default is None
        value = d.get(field.name)
        type_origin = typing.get_origin(field.type)
        type_args = typing.get_args(field.type)

        if value is None and not optional:
            raise ConfigError(f"missing required field {field.name}")

        if value is None and optional:
            continue

        if optional:
            typechekd = field.type is Optional[type(value)]
        elif type_origin is Union:
            typechekd = col.contains(type(value), type_args)
        else:
            typechekd = field.type is type(value)

        if not typechekd:
            raise ConfigError(
                f"mismatching type for {field.name}. Expected: {field.type} received {type(value)}"
            )
    try:
        return cls(**d)
    except TypeError as e:
        raise ConfigError(f"error loading {cls}: {e}")


def load_dict(cls, d: dict):
    return {k: load_class_from_dict(cls, v) for k, v in d.items()}
