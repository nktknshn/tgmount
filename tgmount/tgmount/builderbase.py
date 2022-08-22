import abc
from abc import abstractmethod
from collections.abc import Awaitable, Callable, Mapping
from typing import Optional, Type

from dataclasses import dataclass, replace

from telethon.tl.custom import Message

from tgmount import config, tg_vfs, tgclient, vfs
from tgmount.cache import CacheFactory
from tgmount.cache import source
from tgmount.cache.source import FilesSourceCaching
from tgmount.config import Config, ConfigValidator
from tgmount.config.types import MessageSource
from tgmount.tg_vfs.file_factory import FileFactory
from tgmount.tgclient import TelegramMessageSource, TgmountTelegramClient
from tgmount.util import col, compose_guards

from .base2 import CreateRootResources, Tgmount
from .types import (
    CachesProviderProto,
    DirWrapper,
    DirWrapperProviderProto,
    Filter,
    FilterProviderProto,
    TgmountRoot,
)


@dataclass
class Context:
    current_path: list[str]
    source: Optional[TelegramMessageSource] = None
    # filt: str | dict[str, dict] | list[str | dict[str, dict]]

    def set_source(self, source: Optional[TelegramMessageSource]):
        return replace(self, source=source)

    def add_path(self, element: str):
        return replace(self, current_path=[*self.current_path, element])


def to_dicts(items: list[str | dict[str, dict]]) -> list[str | dict[str, dict]]:
    res = []

    for item in items:
        if isinstance(item, str):
            res.append(item)
        else:
            res.extend(dict([t]) for t in item.items())

    return res


async def _apply_filter(
    messages: list[Message],
    filt: str | dict[str, dict] | list[str | dict[str, dict]],
    *,
    resources: CreateRootResources,
    ctx: Context,
):
    if not isinstance(filt, list):
        filt = [filt]

    filt = to_dicts(filt)

    fs: list[Filter] = []

    for f_item in filt:
        if isinstance(f_item, str):
            filter_cons = resources.filters.get(f_item)
            filter_arg = None
        else:
            f_name, filter_arg = next(iter(f_item.items()))
            filter_cons = resources.filters.get(f_name)

        if filter_cons is None:
            raise config.ConfigError(f"missing filter: {f_item} in {ctx.current_path}")

        fs.append(
            filter_cons()
            if filter_arg is None
            else filter_cons.from_config(filter_arg),
        )

    for filter_cons in fs:
        messages = filter_cons.filter(messages)

    return messages


async def _process_source(
    d: dict,
    ms: TelegramMessageSource,
    file_factory: FileFactory,
    content: list,
    *,
    resources: CreateRootResources,
    ctx: Context,
) -> Context:
    filt = d.get("filter")

    messages = await ms.get_messages()
    messages = [m for m in messages if file_factory.supports(m)]

    if filt is not None:
        messages = await _apply_filter(
            messages,
            filt,
            resources=resources,
            ctx=ctx,
        )

    for m in messages:
        content.append(file_factory.file(m))

    # if recursive:
    #     return ctx.set_source(ms)

    return ctx


async def _tgmount_root(
    d: dict, *, resources: CreateRootResources, ctx=Context(current_path=[])
) -> vfs.DirContentProto:
    source = d.get("source")
    filt = d.get("filter")
    cache = d.get("cache")
    wrappers = d.get("wrappers")

    other_keys = set(d.keys()).difference(
        {"source", "filter", "cache", "wrappers"},
    )

    file_factory = (
        resources.file_factory if cache is None else resources.caches.get(cache)
    )

    if file_factory is None:
        raise config.ConfigError(f"missing cache named {cache} in {ctx.current_path}")

    content = []

    if source is not None:

        if isinstance(source, str):
            source_name = source
            recursive = False
        else:
            source_name = source["source"]
            recursive = source["recursive"]

        ms = resources.sources.get(source_name)

        if ms is None:
            raise config.ConfigError(
                f"missing message source {source} in {ctx.current_path}"
            )

        if not recursive:
            await _process_source(
                d,
                ms,
                file_factory,
                content,
                resources=resources,
                ctx=ctx,
            )

        if recursive:
            ctx = ctx.set_source(ms)

    elif ctx.source is not None and filt is not None:
        await _process_source(
            d,
            ctx.source,
            file_factory,
            content,
            resources=resources,
            ctx=ctx,
        )
    elif len(other_keys) == 0:
        raise config.ConfigError(f"missing source or subfolders in {ctx.current_path}")

    for k in other_keys:
        _content = await _tgmount_root(
            d[k],
            resources=resources,
            ctx=ctx.add_path(k),
        )
        content.append(vfs.vdir(k, _content))

    content = vfs.dir_content(*content)

    if wrappers is not None:
        if not isinstance(wrappers, list):
            wrappers = [wrappers]

        for w_name in wrappers:
            w = resources.wrappers.get(w_name)

            if w is None:
                raise config.ConfigError(f"missing wrapper: {w} in {ctx.current_path}")

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
        client = await self.create_client(cfg)
        messssage_sources = {
            k: await self.create_message_source(client, ms)
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
            mount_dir=cfg.mount_dir,
            wrappers=wrappers,
            caches=caches,
            root=self.parse_root_dict(cfg.root.content),
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

    async def create_client(self, cfg: Config):
        return self.TelegramClient(
            cfg.client.session,
            cfg.client.api_id,
            cfg.client.api_hash,
        )

    async def create_message_source(
        self,
        client: tgclient.TgmountTelegramClient,
        ms: config.MessageSource,
    ) -> tgclient.TelegramMessageSource:
        return self.MessageSource(client, ms.entity, ms.limit)

    def parse_root_dict(self, d: dict) -> TgmountRoot:
        return lambda ctx: _tgmount_root(
            d,
            resources=ctx,
        )
