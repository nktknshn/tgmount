from typing import Optional, TypeVar
from .guards import compose_guards
from .col import find

T = TypeVar("T")


def none_fallback(value: Optional[T], default: T) -> T:
    return value if value is not None else default
