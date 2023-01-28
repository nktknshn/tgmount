from abc import abstractmethod
from dataclasses import dataclass
from typing import Awaitable, Callable, Mapping, Type

from tgmount import vfs
from tgmount.tgclient.guards import *
from tgmount.util import is_not_none, none_fallback
from .error import FileFactoryError
from .types import FileFactoryProto

T = TypeVar("T")
C = TypeVar("C", bound=WithTryGetMethodProto)


TryGetFunc = Callable[[MessageProto], Optional[T]]

SupportedClass = WithTryGetMethodProto[T]
FilenameGetter = Callable[[T], Awaitable[str]] | Callable[[T], str]
FileContentGetter = (
    Callable[[T], Awaitable[vfs.FileContentProto]] | Callable[[T], vfs.FileContentProto]
)

FileGetter = (
    Callable[[T, Optional[str]], Awaitable[vfs.FileLike]]
    | Callable[[T, Optional[str]], vfs.FileLike]
)

ClassName = str


@dataclass
class FileFactoryItem:
    klass: Type[WithTryGetMethodProto]
    filename: FilenameGetter
    content: Optional[FileContentGetter]
    file: Optional[FileGetter]


async def resolve_future_or_value(future_or_value: T | Awaitable[T]) -> T:
    if isinstance(future_or_value, Awaitable):
        return await future_or_value

    return future_or_value


class FileFactoryBase(FileFactoryProto[T], abc.ABC):
    """Takes a message and produces vfs.FileLike or vfs.FileContentProto"""

    _supported: dict[ClassName, FileFactoryItem] = {}

    def __init__(self, factory_props: Mapping | None = None) -> None:
        self._cache: dict[MessageProto, Optional[Type[T]]] = {}
        self._factory_props = factory_props

    @property
    def try_get_dict(self) -> Mapping[str, Type[TryGetFunc]]:
        return {f.__name__: f.try_get for f in self.supported}

    def message_type(self, item: T):
        return self.get_cls(item)

    def message_types(self, item: T):
        return [self.get_cls(item)]

    @classmethod
    def unregister(cls, klass: Type[C]):
        class_name = klass.__name__
        del cls._supported[class_name]

    @classmethod
    def register(
        cls,
        klass: Type[C],
        filename: FilenameGetter[C],
        file_content: Optional[FileContentGetter[C]] = None,
        file_getter: Optional[FileGetter[C]] = None,
    ):
        class_name = klass.__name__
        cls._supported = {**cls._supported}
        cls._supported[class_name] = FileFactoryItem(
            klass=klass,
            filename=filename,
            content=file_content,
            file=file_getter,
        )

    @property
    def supported(self) -> list[Type[SupportedClass]]:
        return list(map(lambda item: item.klass, self._supported.values()))

    def supports(
        self, input_item: Any, *, factory_props: Mapping | None = None
    ) -> bool:
        return self.try_get(input_item, factory_props=factory_props) is not None

    def get_supported(
        self, input_items: list[Any], *, factory_props: Mapping | None = None
    ) -> list[T]:
        return list(
            filter(
                is_not_none,
                map(
                    lambda item: self.try_get(item, factory_props=factory_props),
                    input_items,
                ),
            )
        )

    def try_get(
        self, input_item: Any, *, factory_props: Mapping | None = None
    ) -> Optional[T]:
        # if input_item in self._cache:
        # return self._cache[input_item]

        if (
            klass := self.try_get_cls(input_item, factory_props=factory_props)
        ) is not None:
            msg = klass.try_get(input_item)
            # self._cache[input_item] = msg

            return msg

        # self._cache[input_item] = None
        return None

    def try_get_cls(
        self, input_item: Any, *, factory_props: Mapping | None = None
    ) -> Optional[Type[T]]:

        factory_props = none_fallback(
            factory_props, none_fallback(self._factory_props, {})
        )

        treat_as = none_fallback(factory_props.get("treat_as"), [])

        for cls_name in treat_as:
            if (klass := self._supported.get(cls_name)) is not None:
                if (m := klass.klass.try_get(input_item)) is not None:
                    return klass.klass

        for klass in self.supported:
            if (m := klass.try_get(input_item)) is not None:
                return klass

        return None

    def get_cls(
        self, supported_item: T, *, factory_props: Mapping | None = None
    ) -> Type[T]:

        klass = self.try_get_cls(supported_item, factory_props=factory_props)

        if klass is None:
            raise FileFactoryError(f"{supported_item} is not supported.")

        return klass

    def get_cls_item(
        self, supported_item: T, *, factory_props: Mapping | None = None
    ) -> FileFactoryItem:
        class_name = self.get_cls(supported_item, factory_props=factory_props).__name__
        return self._supported[class_name]

    async def size(
        self, supported_item: T, *, factory_props: Mapping | None = None
    ) -> int:
        return (
            await self.file_content(supported_item, factory_props=factory_props)
        ).size

    async def filename(
        self, supported_item: T, *, factory_props: Mapping | None = None
    ) -> str:
        fname = self.get_cls_item(supported_item, factory_props=factory_props).filename(
            supported_item
        )

        return await resolve_future_or_value(fname)

    @abstractmethod
    async def file(
        self, supported_item: T, name=None, *, factory_props: Mapping | None = None
    ) -> vfs.FileLike:
        ...

    @abstractmethod
    async def file_content(
        self, supported_item: T, *, factory_props: Mapping | None = None
    ) -> vfs.FileContent:
        ...
