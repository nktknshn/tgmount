import yaml
from dataclasses import dataclass, fields
from typing import Optional, Union, Mapping
import typing
from tgmount.util import col
from tgmount import vfs

from .helpers import *
from .root import *


@dataclass
class Cache:
    type: str
    kwargs: dict
    # capacity: str
    # block_size: str

    @staticmethod
    def from_dict(d: dict) -> "Cache":
        return load_class_from_dict(
            Cache,
            d,
            loaders={"kwargs": lambda d: col.dict_exclude(d, ["type"])},
        )


@dataclass
class Caches:
    caches: dict[str, Cache]

    @staticmethod
    def from_dict(d: dict) -> "Caches":
        return Caches(
            caches=load_dict(Cache.from_dict, d),
        )


@dataclass
class Wrapper:
    type: str
    kwargs: dict

    @staticmethod
    def from_dict(d: dict) -> "Wrapper":
        return load_class_from_dict(
            Wrapper,
            d,
            loaders={"kwargs": lambda d: col.dict_exclude(d, ["type"])},
        )


@dataclass
class Wrappers:
    wrappers: dict[str, Wrapper]

    @staticmethod
    def from_dict(d: dict) -> "Wrappers":
        return Wrappers(
            wrappers=load_dict(Wrapper.from_dict, d),
        )


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

        # assert_that(
        #     len(d) > 0,
        #     ConfigError(f"`message_sources` must contain at least one record."),
        # )

        return MessageSources(load_dict(MessageSource, d))


@dataclass
class Config:
    client: Client
    message_sources: MessageSources
    root: Root
    caches: Optional[Caches] = None
    wrappers: Optional[Wrappers] = None
    mount_dir: Optional[str] = None

    @staticmethod
    def from_dict(d: dict):
        client_dict = d.get("client")
        message_sources_dict = d.get("message_sources")
        root_dict = d.get("root")
        caches_dict = d.get("caches")
        wrappers_dict = d.get("wrappers")

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
            wrappers=Wrappers.from_dict(wrappers_dict)
            if wrappers_dict is not None
            else None,
        )

    @staticmethod
    def from_yaml(s):
        return Config.from_dict(yaml.safe_load(s))
