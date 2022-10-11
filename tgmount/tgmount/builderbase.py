import abc
from typing import Protocol, Type

from tgmount import cache, config, tgclient, tglog
from tgmount.tgclient import TgmountTelegramClient

from .file_factory import classifier, FileFactoryDefault
from .providers.provider_caches import CachesProviderProto
from .providers.provider_filters import FilterProviderProto
from .providers.provider_sources import SourcesProvider
from .providers.provider_wrappers import DirWrapperProviderProto
from .providers.provider_producers import ProducersProviderBase

from .tgmount_types import TgmountResources
from .tgmountbase import TgmountBase


class TgmountBuilderBase(abc.ABC):
    logger = tglog.getLogger(f"TgmountBuilderBase()")

    TelegramClient: Type[tgclient.client_types.TgmountTelegramClientReaderProto]
    MessageSource: Type[tgclient.TelegramMessageSource]
    FilesSource: Type[tgclient.TelegramFilesSource]
    FileFactory: Type[FileFactoryDefault]
    FilesSourceCaching: Type[cache.FilesSourceCaching]
    SourcesProvider: Type[SourcesProvider]

    classifier: classifier.ClassifierBase
    caches: CachesProviderProto
    filters: FilterProviderProto
    wrappers: DirWrapperProviderProto
    producers: ProducersProviderBase

    TgmountBase = TgmountBase

    async def create_client(self, cfg: config.Config, **kwargs):
        return self.TelegramClient(
            cfg.client.session,
            cfg.client.api_id,
            cfg.client.api_hash,
            **kwargs,
        )

    async def create_resources(
        self,
        client: tgclient.client_types.TgmountTelegramClientReaderProto,
        cfg: config.Config,
    ):
        self.logger.trace(f"Creating resources...")

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

        message_sources = self.SourcesProvider(
            {
                k: self.MessageSource(client, ms.entity, ms.limit)
                for k, ms in cfg.message_sources.sources.items()
            }
        )

        for src in message_sources.as_mapping().values():
            src.filters.append(file_factory.supports)

        return TgmountResources(
            file_factory=file_factory,
            sources=message_sources,
            filters=self.filters.get_filters(),
            producers=self.producers,
            caches=cached_factories,
            wrappers=self.wrappers.get_wrappers(),
            classifier=self.classifier,
            vfs_wrappers={},
        )

    async def create_tgmount(self, cfg: config.Config) -> TgmountBase:

        self.client = await self.create_client(cfg)
        self.resources = await self.create_resources(self.client, cfg)

        tgm = self.TgmountBase(
            client=self.client,
            root=cfg.root.content,
            resources=self.resources,
            mount_dir=cfg.mount_dir,
        )

        return tgm

    async def create_cache(
        self,
        client: tgclient.client_types.TgmountTelegramClientReaderProto,
        cache_config: config.Cache,
    ):
        cache_factory_cls = await self.caches.get_cache_factory(cache_config.type)
        return cache_factory_cls(**cache_config.kwargs)
