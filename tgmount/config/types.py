from dataclasses import dataclass, fields
from typing import Optional, Union
import typing
from tgmount.util import col
from tgmount import vfs

from .helpers import *
from .root import *


@dataclass
class Cache:
    type: str
    capacity: str
    block_size: str

    @staticmethod
    def from_dict(d: dict) -> "Cache":
        return load_class_from_dict(Cache, d)


@dataclass
class Caches:
    caches: dict[str, Cache]

    @staticmethod
    def from_dict(d: dict) -> "Caches":
        return Caches(caches=load_dict(Cache, d))


@dataclass
class Client:
    session: str
    api_id: int
    api_hash: str

    @staticmethod
    def from_dict(d: dict) -> "Client":
        return load_class_from_dict(Client, d)


@dataclass
class MessageSource:
    entity: Union[str, int]
    filter: Optional[str] = None
    limit: Optional[int] = None
    reverse: Optional[bool] = None
    updates: Optional[bool] = None

    @staticmethod
    def from_dict(d: dict) -> "MessageSource":
        return load_class_from_dict(MessageSource, d)


@dataclass
class MessageSources:
    sources: dict[str, MessageSource]

    @staticmethod
    def from_dict(d: dict) -> "MessageSources":

        assert_that(
            len(d) > 0,
            ConfigError(f"message_sources must contain at least one record."),
        )

        return MessageSources(load_dict(MessageSource, d))


@dataclass
class Config:
    client: Client
    message_sources: MessageSources
    root: Root
    caches: Optional[Caches] = None
    mount_dir: Optional[str] = None

    @staticmethod
    def from_dict(d: dict):
        client_dict = d.get("client")
        message_sources_dict = d.get("message_sources")
        root_dict = d.get("root")
        caches_dict = d.get("caches")

        if client_dict is None:
            raise ConfigError("Missing 'client'")

        if message_sources_dict is None:
            raise ConfigError("Missing 'message_sources'")

        if root_dict is None:
            raise ConfigError("Missing 'root'")

        return Config(
            mount_dir=d.get("mount_dir"),
            client=Client.from_dict(client_dict),
            message_sources=MessageSources.from_dict(message_sources_dict),
            root=Root.from_dict(root_dict),
            caches=Caches.from_dict(caches_dict) if caches_dict is not None else None,
        )
