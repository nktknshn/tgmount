from abc import abstractmethod
from collections.abc import Callable, Mapping
from typing import Any, Optional, Protocol, Type, TypeVar

from tgmount.tgclient import guards

I = TypeVar("I")
I_contr = TypeVar("I_contr", contravariant=True)

O = TypeVar("O")


class ClassifierProto(Protocol[I_contr, O]):
    @abstractmethod
    def classify(self, input_item: I_contr) -> list[Type[O]]:
        ...

    @abstractmethod
    def try_get_guard(self, class_name: str) -> Optional[Callable[[Any], bool]]:
        ...


TG = TypeVar("TG", bound=guards.ClassWithGuard)


class ClassifierBase(ClassifierProto[Any, TG]):
    """Takes a message and return a list of classes this message suits"""

    classes: list[Type[TG]]

    @classmethod
    @property
    def classes_dict(cls) -> Mapping[str, Type[TG]]:
        return {k.__name__: k for k in cls.classes}

    def try_get_guard(self, class_name: str) -> Optional[Callable[[Any], bool]]:
        if (klass := self.classes_dict.get(class_name)) is not None:
            return klass.guard

    def classify_str(self, input_item: Any) -> list[str]:
        return list(map(lambda k: k.__name__, self.classify(input_item)))

    def classify(self, input_item: Any) -> list[Type[TG]]:
        klasses: list[Type[TG]] = []

        for klass in self.classes:
            if klass.guard(input_item):
                klasses.append(klass)

        return klasses

    @classmethod
    def register(cls, klass: Type[TG]):
        cls.classes = [*cls.classes, klass]
