import abc
from dataclasses import replace
from typing import Type

from tgmount import cache, config, tgclient
from tgmount.cache.types import CacheInBlocksProto
from tgmount.tgclient.events_disptacher import (
    TelegramEventsDispatcher,
)
from tgmount.tgclient.fetcher import TelegramMessagesFetcher
from tgmount.tgmount import cached_filefactory_factory
from tgmount.tgmount.cached_filefactory_factory import (
    CacheFileFactoryFactory,
    CacheFileFactoryFactoryProto,
)

from tgmount.tgmount.providers.provider_vfs_wrappers import ProviderVfsWrappersBase
from tgmount.tgmount.root_config_reader import TgmountConfigReader
from tgmount.tgmount.vfs_tree import VfsTree
from tgmount.tgmount.vfs_tree_producer import VfsTreeProducer
from tgmount.util import none_fallback

from .file_factory import classifier, FileFactoryDefault
from .providers.provider_caches import CachesTypesProviderProto
from .providers.provider_filters import FilterProviderProto
from .providers.provider_producers import ProducersProviderBase
from .providers.provider_sources import SourcesProvider

from .tgmount_types import TgmountResources
from .tgmountbase import TgmountBase
from .logger import module_logger as _logger


class TgmountBuilderBase(abc.ABC):
    """Construct TgmountBase from a config"""

    logger = _logger.getChild(f"TgmountBuilderBase")

    TelegramClient: Type[tgclient.client_types.TgmountTelegramClientReaderProto]
    MessageSource: Type[tgclient.MessageSource]
    FilesSource: Type[tgclient.TelegramFilesSource]
    FileFactory: Type[FileFactoryDefault]
    FilesSourceCached: Type[cache.FilesSourceCached]
    CacheFileFactoryFactory: Type[CacheFileFactoryFactory]

    TgmountBase = TgmountBase
    TelegramMessagesFetcher = TelegramMessagesFetcher
    TelegramEventsDispatcher = TelegramEventsDispatcher
    VfsTree = VfsTree
    VfsTreeProducer = VfsTreeProducer

    classifier: classifier.ClassifierBase
    caches: CachesTypesProviderProto
    filters: FilterProviderProto
    wrappers: ProviderVfsWrappersBase
    producers: ProducersProviderBase

    async def create_client(self, cfg: config.Config, **kwargs):
        return self.TelegramClient(
            cfg.client.session,
            cfg.client.api_id,
            cfg.client.api_hash,
            **kwargs,
        )

    # async def create_cache_factory(
    #     self,
    #     client: tgclient.client_types.TgmountTelegramClientReaderProto,
    #     cache_config: config.Cache,
    # ) -> CacheProto:
    #     cache_factory_cls = self.caches.get_cache_factory(cache_config.type)
    #     return cache_factory_cls(**cache_config.kwargs)

    async def create_vfs_tree(self):
        return self.VfsTree()

    async def create_file_source(self, cfg: config.Config, client):
        return self.FilesSource(client)

    async def create_file_factory(self, cfg: config.Config, client, files_source):
        return self.FileFactory(files_source)

    async def create_cached_filefactory_factory(self, cfg: config.Config, client):
        self.cached_filefactory_factory = self.CacheFileFactoryFactory(
            client, self.caches
        )
        return self.cached_filefactory_factory

    async def create_events_dispatcher(self, cfg: config.Config, client):
        return self.TelegramEventsDispatcher()

    async def create_message_source(
        self, cfg: config.Config, client, msc: config.MessageSource
    ):
        return self.MessageSource(tag=msc.entity)

    async def create_fetcher(
        self,
        cfg: config.Config,
        client,
        msc: config.MessageSource,
        message_source,
    ):
        return self.TelegramMessagesFetcher(client, msc)

    async def create_tgmount_resources(self, client, cfg: config.Config, **kwargs):

        sources_used_in_root = await TgmountConfigReader().get_used_sources(
            cfg.root.content
        )

        files_source = await self.create_file_source(cfg, client)
        file_factory = await self.create_file_factory(cfg, client, files_source)

        source_provider = SourcesProvider()

        fetchers_dict = {}

        for k, msc in cfg.message_sources.sources.items():
            if k not in list(sources_used_in_root):
                continue

            message_source = await self.create_message_source(cfg, client, msc)
            message_source.add_filter(file_factory.supports)

            fetcher = await self.create_fetcher(cfg, client, msc, message_source)

            fetchers_dict[k] = fetcher

            source_provider.add_source(k, message_source)

        # caches: dict[str, cache.CacheFactory] = {}
        # cached_factories = {}
        # cached_sources = {}

        await self.create_cached_filefactory_factory(cfg, client)

        caches_config = cfg.caches.caches if cfg.caches is not None else {}

        for cache_id, cache_config in caches_config.items():
            await self.cached_filefactory_factory.create_cached_filefactory(
                cache_id, cache_config.type, cache_config.kwargs
            )

            # cached_factories[k] = fc

        return TgmountResources(
            message_sources=source_provider,
            fetchers_dict=fetchers_dict,
            caches=self.cached_filefactory_factory,
            # caches=cached_factories,
            # cache_provider=self.caches,
            file_factory=file_factory,
            filters=self.filters,
            producers=self.producers,
            classifier=self.classifier,
            vfs_wrappers=self.wrappers,
            extra=await self.create_extra(),
        )

    async def create_extra(self):
        return {
            "get_tgm": lambda: self.tgm,
        }

    async def create_tgmount(self, cfg: config.Config, **kwargs) -> TgmountBase:
        self.client = await self.create_client(cfg, **kwargs)
        self.resources = await self.create_tgmount_resources(self.client, cfg)

        self.tgm = tgm = self.TgmountBase(
            client=self.client,
            resources=self.resources,
            root_config=cfg.root.content,
            mount_dir=cfg.mount_dir,
        )

        tgm.producer = self.VfsTreeProducer(resources=self.resources)
        tgm.vfs_tree = await self.create_vfs_tree()
        tgm.events_dispatcher = self.TelegramEventsDispatcher()

        for k, msc in cfg.message_sources.sources.items():

            ms = self.resources.message_sources.get(k)

            if ms is None:
                continue

            updates = none_fallback(msc.updates, True)

            if not updates:
                continue

            self.client.subscribe_new_messages(
                lambda ev, eid=msc.entity: tgm.on_new_message(eid, ev), chats=msc.entity
            )
            self.client.subscribe_removed_messages(
                lambda ev, eid=msc.entity: tgm.on_delete_message(eid, ev),
                chats=msc.entity,
            )
            self.client.subscribe_edited_message(
                lambda ev, eid=msc.entity: tgm.on_edited_message(eid, ev),
                chats=msc.entity,
            )

            tgm.events_dispatcher.connect(msc.entity, ms)

        return tgm
