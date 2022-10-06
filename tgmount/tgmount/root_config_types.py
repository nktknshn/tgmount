from dataclasses import dataclass, replace
from typing import Optional

from tgmount.tgclient import MessageSourceSubscribableProto, MessageSourceProto
from tgmount.tgmount.file_factory import FileFactoryProto, ClassifierBase
from tgmount.tgmount.filters import Filter
from tgmount.tgmount.tgmount_types import TgmountResources
from tgmount.util import none_fallback


@dataclass
class ReadRootConfigContext:
    """Immutable context to traverse root config dictionary"""

    current_path: list[str]
    file_factory: FileFactoryProto
    classifier: ClassifierBase
    recursive_source: Optional[MessageSourceSubscribableProto] = None
    recursive_filters: Optional[list[Filter]] = None

    def set_recursive_source(self, source: Optional[MessageSourceProto]):
        return replace(self, recursive_source=source)

    def set_recursive_filters(self, recursive_filters: Optional[list[Filter]]):
        return replace(self, recursive_filters=recursive_filters)

    def extend_recursive_filters(self, filters: list[Filter]):
        return replace(
            self,
            recursive_filters=[*none_fallback(self.recursive_filters, []), *filters],
        )

    def set_file_factory(self, file_factory: FileFactoryProto):
        return replace(self, file_factory=file_factory)

    def add_path(self, element: str):
        return replace(self, current_path=[*self.current_path, element])

    def set_path(self, path: list[str]):
        return replace(self, current_path=path)

    @staticmethod
    def from_resources(
        resources: TgmountResources,
        current_path: list[str] | None = None,
        recursive_source: Optional[MessageSourceSubscribableProto] = None,
    ):
        return ReadRootConfigContext(
            current_path=none_fallback(current_path, []),
            recursive_source=recursive_source,
            file_factory=resources.file_factory,
            classifier=resources.classifier,
        )
