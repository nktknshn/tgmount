import abc
from abc import abstractmethod
from collections.abc import Awaitable, Callable, Mapping
from typing import Type
from tgmount.config import Config, ConfigValidator
from tgmount import config
from tgmount.tg_vfs.file_factory import FileFactory
from tgmount.tgclient import TgmountTelegramClient, TelegramMessageSource
from tgmount.tgmount import TgmountBase
from tgmount.util import col, compose_guards
from tgmount import vfs, tg_vfs, tgclient

from .types import Filter, TgmountRoot, FilterProviderProto
from .base2 import CreateRootContext, Tgmount


async def _tgmount_root(d: dict, *, ctx: CreateRootContext) -> vfs.DirContentProto:
    source = d.get("source")
    filt = d.get("filter")
    cache = d.get("cache")
    wrappers = d.get("wrappers")

    other_keys = set(d.keys()).difference({"source", "filter", "cache", "wrappers"})

    print(other_keys)
    content = []

    if source is not None:
        ms = ctx.sources.get(source)

        if ms is None:
            raise config.ConfigError(f"missing message source {source}")

        messages = await ms.get_messages()

        if filt is not None:
            if not isinstance(filt, list):
                filt = [filt]

            fs = []
            for f_name in filt:
                f = ctx.filters.get(f_name)
                if f is None:
                    raise config.ConfigError(f"missing some of the filters: {f_name}")
                fs.append(f)

            g = compose_guards(*fs)

            messages = [m for m in messages if g(m)]
        else:
            messages = [m for m in messages if ctx.file_factory.supports(m)]

        for m in messages:
            content.append(ctx.file_factory.file(m))

    for k in other_keys:
        _content = await _tgmount_root(
            d[k],
            ctx=ctx,
        )
        content.append(vfs.vdir(k, _content))

    return vfs.dir_content(*content)


class TgmountBuilderBase(abc.ABC):
    TelegramClient: Type[tgclient.TgmountTelegramClient]
    MessageSource: Type[tgclient.TelegramMessageSource]
    FilesSource: Type[tgclient.TelegramFilesSource]
    FileFactory: Type[tg_vfs.FileFactory]

    filters: FilterProviderProto

    async def create_tgmount(self, cfg: Config) -> Tgmount:
        client = self.create_client(cfg)
        messssage_sources = {
            k: self.create_message_source(client, ms)
            for k, ms in cfg.message_sources.sources.items()
        }

        files_source = self.FilesSource(client)
        file_factory = self.FileFactory(files_source)

        tgm = Tgmount(
            client=client,
            file_factory=file_factory,
            filters=self.filters.get_filters(),
            message_sources=messssage_sources,
            root=self.parse_root_dict(cfg.root.content),
            mount_dir=cfg.mount_dir,
        )

        for k, v in messssage_sources.items():
            v.subscribe(tgm.update)

        return tgm

    def create_client(self, cfg: Config):
        return self.TelegramClient(
            cfg.client.session,
            cfg.client.api_id,
            cfg.client.api_hash,
        )

    def create_message_source(
        self,
        client: tgclient.TgmountTelegramClient,
        ms: config.MessageSource,
    ) -> tgclient.TelegramMessageSource:
        return self.MessageSource(client, ms.entity, ms.limit)

    def parse_root_dict(self, d: dict) -> TgmountRoot:
        return lambda ctx: _tgmount_root(
            d,
            ctx=ctx,
        )
