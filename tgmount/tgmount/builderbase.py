import abc
from abc import abstractmethod
from collections.abc import Awaitable, Callable, Mapping
from typing import Type
from tgmount.cache import CacheFactory
from tgmount.cache.source import FilesSourceCaching
from tgmount.config import Config, ConfigValidator
from tgmount import config
from tgmount.tg_vfs.file_factory import FileFactory
from tgmount.tgclient import TgmountTelegramClient, TelegramMessageSource
from tgmount.util import col, compose_guards
from tgmount import vfs, tg_vfs, tgclient

from .types import (
    CachesProviderProto,
    DirWrapper,
    Filter,
    TgmountRoot,
    FilterProviderProto,
    DirWrapperProviderProto,
)
from .base2 import CreateRootContext, Tgmount


async def _tgmount_root(
    d: dict, *, ctx: CreateRootContext, current_path=[]
) -> vfs.DirContentProto:
    source = d.get("source")
    filt = d.get("filter")
    cache = d.get("cache")
    wrappers = d.get("wrappers")

    print(wrappers)

    other_keys = set(d.keys()).difference(
        {"source", "filter", "cache", "wrappers"},
    )

    file_factory = ctx.file_factory if cache is None else ctx.caches.get(cache)

    if file_factory is None:
        raise config.ConfigError(f"missing cache named {cache} in {current_path}")

    content = []

    if source is not None:
        ms = ctx.sources.get(source)

        if ms is None:
            raise config.ConfigError(
                f"missing message source {source} in {current_path}"
            )

        messages = await ms.get_messages()

        if filt is not None:
            if not isinstance(filt, list):
                filt = [filt]

            fs = []
            for f_name in filt:
                f = ctx.filters.get(f_name)
                if f is None:
                    raise config.ConfigError(
                        f"missing filter: {f_name} in {current_path}"
                    )
                fs.append(f)

            g = compose_guards(*fs)

            messages = [m for m in messages if g(m)]
        else:
            messages = [m for m in messages if file_factory.supports(m)]

        for m in messages:
            content.append(file_factory.file(m))

    if source is None and len(other_keys) == 0:
        raise config.ConfigError(f"missing source or subfolders in {current_path}")

    for k in other_keys:
        _content = await _tgmount_root(d[k], ctx=ctx, current_path=[*current_path, k])
        content.append(vfs.vdir(k, _content))

    content = vfs.dir_content(*content)

    if wrappers is not None:
        if not isinstance(wrappers, list):
            wrappers = [wrappers]

        for w_name in wrappers:
            w = ctx.wrappers.get(w_name)

            if w is None:
                raise config.ConfigError(f"missing wrapper: {w} in {current_path}")

            content = await w(content)

    return content


class TgmountBuilderBase(abc.ABC):
    TelegramClient: Type[tgclient.TgmountTelegramClient]
    MessageSource: Type[tgclient.TelegramMessageSource]
    FilesSource: Type[tgclient.TelegramFilesSource]
    FileFactory: Type[tg_vfs.FileFactory]

    caches: CachesProviderProto
    filters: FilterProviderProto
    wrappers: DirWrapperProviderProto

    async def create_tgmount(self, cfg: Config) -> Tgmount:
        client = self.create_client(cfg)
        messssage_sources = {
            k: self.create_message_source(client, ms)
            for k, ms in cfg.message_sources.sources.items()
        }

        if cfg.caches is not None:
            caches = {
                k: await self.create_cached_file_source(client, cache_config)
                for k, cache_config in cfg.caches.caches.items()
            }
        else:
            caches = {}

        if cfg.wrappers is not None:
            wrappers = {
                k: await self.create_wrapper(wrapper_config)
                for k, wrapper_config in cfg.wrappers.wrappers.items()
            }
        else:
            wrappers = {}

        files_source = self.FilesSource(client)
        file_factory = self.FileFactory(files_source)

        tgm = Tgmount(
            client=client,
            file_factory=file_factory,
            filters=self.filters.get_filters(),
            message_sources=messssage_sources,
            root=self.parse_root_dict(cfg.root.content),
            mount_dir=cfg.mount_dir,
            wrappers=wrappers,
            caches=caches,
        )

        for k, v in messssage_sources.items():
            v.subscribe(tgm.update)

        return tgm

    async def create_cached_file_source(
        self, client: TgmountTelegramClient, cache_config: config.Cache
    ) -> tg_vfs.FileFactory:
        cache_factory_cls = await self.caches.get_cache_factory(cache_config.type)

        cache = cache_factory_cls(**cache_config.kwargs)

        fsc = FilesSourceCaching(client, cache)

        return self.FileFactory(fsc)

    async def create_wrapper(self, w: config.Wrapper) -> DirWrapper:
        cons = await self.wrappers.get_wrappers_factory(w.type)

        return await cons(**w.kwargs)

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
