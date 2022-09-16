import abc
from typing import Mapping, Type

from telethon.tl.custom import Message

from tgmount import cache, config, tg_vfs, tgclient
from tgmount.tg_vfs import classifier
from tgmount.tgclient import TgmountTelegramClient
from tgmount.tgmount.exclude_empty import ExcludeEmptyWrappr
from tgmount.tgmount.provider_sources import SourcesProvider
from tgmount.tgmount.vfs_structure_producers_provider import VfsProducersProviderProto

from .caches import CachesProviderProto
from .filters import FilterProviderProto
from .tgmountbase import Tgmount
from .types import CreateRootResources, SourcesProviderProto, TgmountRoot
from .wrappers import DirWrapperProviderProto
from .tgmount_root_producer import TgmountRootProducer


class TgmountBuilderBase(abc.ABC):
    TelegramClient: Type[tgclient.TgmountTelegramClient]
    MessageSource: Type[tgclient.TelegramMessageSource]
    FilesSource: Type[tgclient.TelegramFilesSource]
    FileFactory: Type[tg_vfs.FileFactoryDefault]
    FilesSourceCaching: Type[cache.FilesSourceCaching]
    SourcesProvider: Type[SourcesProvider]

    classifier: classifier.ClassifierBase
    caches: CachesProviderProto
    filters: FilterProviderProto
    wrappers: DirWrapperProviderProto
    producers: VfsProducersProviderProto

    async def create_client(self, cfg: config.Config):
        return self.TelegramClient(
            cfg.client.session,
            cfg.client.api_id,
            cfg.client.api_hash,
        )

    async def create_resources(self, client: TgmountTelegramClient, cfg: config.Config):

        message_sources = self.SourcesProvider(
            {
                k: self.MessageSource(client, ms.entity, ms.limit)
                for k, ms in cfg.message_sources.sources.items()
            }
        )

        caches: dict[str, cache.CacheFactory] = {}
        cached_factories = {}
        cached_sources = {}

        if cfg.caches is not None:
            for k, cache_config in cfg.caches.caches.items():
                cache_factory = await self.create_cache(client, cache_config)
                fsc = self.FilesSourceCaching(client, cache_factory)
                fc = self.FileFactory(fsc, {})

                caches[k] = cache_factory
                cached_sources[k] = fsc
                cached_factories[k] = fc

        files_source = self.FilesSource(client)
        file_factory = self.FileFactory(files_source, cached_factories)

        return CreateRootResources(
            file_factory=file_factory,
            sources=message_sources,
            filters=self.filters.get_filters(),
            producers=self.producers,
            caches=cached_factories,
            wrappers=self.wrappers.get_wrappers(),
            classifier=self.classifier,
            vfs_wrappers={"ExcludeEmptyDirs": ExcludeEmptyWrappr},
        )

    async def create_tgmount(self, cfg: config.Config) -> Tgmount:
        client = await self.create_client(cfg)

        tgm = Tgmount(
            client=client,
            root=cfg.root.content,
            resources=await self.create_resources(client, cfg),
        )

        return tgm

    # async def create_message_source(
    #     self,
    #     client: tgclient.TgmountTelegramClient,
    #     ms: config.MessageSource,
    # ) -> tgclient.TelegramMessageSource:
    #     return self.MessageSource(client, ms.entity, ms.limit)

    async def create_cache(
        self, client: TgmountTelegramClient, cache_config: config.Cache
    ):
        cache_factory_cls = await self.caches.get_cache_factory(cache_config.type)
        return cache_factory_cls(**cache_config.kwargs)

    def parse_root_dict(self, d: dict) -> TgmountRoot:
        return lambda resources: TgmountRootProducer().get_root(d, resources=resources)
