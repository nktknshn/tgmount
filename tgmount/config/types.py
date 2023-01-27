from dataclasses import replace
import datetime
import yaml

from .root import *
import time


DATE_FORMATS = [
    "%d/%m/%Y %H:%M",
    "%d-%m-%Y %H:%M",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d-%m-%y",
    "%d/%m/%y",
]


def parse_datetime(s: str):
    for f in DATE_FORMATS:
        try:
            return datetime.datetime.strptime(s, f)
        except ValueError:
            continue

    raise ConfigError(f"Invalid date: {s}")


@dataclass
class Cache:
    type: str
    kwargs: dict

    @staticmethod
    def from_mapping(d: dict) -> "Cache":
        return load_class_from_mapping(
            Cache,
            d,
            loaders={"kwargs": lambda d: col.dict_exclude(d, ["type"])},
        )


@dataclass
class Caches:
    caches: dict[str, Cache]

    @staticmethod
    def from_mapping(d: dict) -> "Caches":
        return Caches(
            caches=load_mapping(Cache.from_mapping, d),
        )


@dataclass
class Wrapper:
    type: str
    kwargs: dict

    @staticmethod
    def from_mapping(d: dict) -> "Wrapper":
        return load_class_from_mapping(
            Wrapper,
            d,
            loaders={"kwargs": lambda d: col.dict_exclude(d, ["type"])},
        )


@dataclass
class Wrappers:
    wrappers: dict[str, Wrapper]

    @staticmethod
    def from_mapping(d: dict) -> "Wrappers":
        return Wrappers(
            wrappers=load_mapping(Wrapper.from_mapping, d),
        )


@dataclass
class Client:
    session: str
    api_id: int
    api_hash: str

    @staticmethod
    def from_mapping(d: dict) -> "Client":
        return load_class_from_mapping(Client, d)


@dataclass
class MessageSource:
    entity: Union[str, int]
    filter: Optional[str] = None
    limit: Optional[int] = None
    offset_id: int = 0
    min_id: int = 0
    max_id: int = 0
    wait_time: Optional[float] = None
    reply_to: Optional[int] = None
    from_user: Optional[str | int] = None
    reverse: bool = False
    updates: Optional[bool] = None
    offset_date: Optional[datetime.datetime] = None

    @staticmethod
    def from_mapping(d: Mapping) -> "MessageSource":
        return load_class_from_mapping(
            MessageSource,
            d,
            loaders={
                "offset_date": lambda d: parse_datetime(d["offset_date"])
                if "offset_date" in d
                else None
            },
        )


@dataclass
class MessageSources:
    sources: dict[str, MessageSource]

    @staticmethod
    def from_mapping(d: Mapping) -> "MessageSources":
        return MessageSources(load_mapping(MessageSource, d))


@dataclass
class Config:
    client: Client
    message_sources: MessageSources
    root: Root
    caches: Optional[Caches] = None
    wrappers: Optional[Wrappers] = None
    mount_dir: Optional[str] = None

    def set_root(self, root_cfg: Mapping) -> "Config":
        return replace(self, root=replace(self.root, content=root_cfg))

    @staticmethod
    def from_mapping(d: dict):
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
            client=Client.from_mapping(client_dict),
            message_sources=MessageSources.from_mapping(message_sources_dict),
            root=Root.from_dict(root_dict),
            caches=Caches.from_mapping(caches_dict)
            if caches_dict is not None
            else None,
            wrappers=Wrappers.from_mapping(wrappers_dict)
            if wrappers_dict is not None
            else None,
        )

    @staticmethod
    def from_yaml(s):
        return Config.from_mapping(yaml.safe_load(s))
