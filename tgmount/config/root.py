from dataclasses import dataclass, fields
from typing import Optional, Union
import typing
from tgmount.util import col
from tgmount import vfs

RootContentDirs = vfs.Tree["RootContentDir"]
RootTree = vfs.Tree["RootContent"]


@dataclass
class RootContentDir:
    filter: Union[str, list[str]]
    cache: Optional[str] = None


@dataclass
class RootContent:
    source: str
    dirs: RootContentDirs


@dataclass
class Root:
    content: RootTree

    @staticmethod
    def from_dict(d: dict) -> "Root":
        return Root()
