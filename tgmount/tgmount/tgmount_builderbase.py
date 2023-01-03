import abc
from typing import Protocol, Type

from tgmount import cache, config, tgclient, tglog
from tgmount.tgclient.guards import TelegramMessage
from tgmount.tgclient.telegram_message_source import TelegramMessagesFetcher
from tgmount.tgmount.root_config_reader import TgmountConfigReader
from tgmount.tgmount.vfs_tree import VfsTree
from tgmount.util import none_fallback

from .file_factory import classifier, FileFactoryDefault
from .providers.provider_caches import CachesProviderProto
from .providers.provider_filters import FilterProviderProto
from .providers.provider_sources import SourcesProvider
from .providers.provider_wrappers import DirWrapperProviderProto
from .providers.provider_producers import ProducersProviderBase

from .tgmount_types import TgmountResources
from .tgmountbase import TgmountBase


class TgmountBuilderBase(abc.ABC):
    """Construct TgmountBase from a config"""

    logger = tglog.getLogger(f"TgmountBuilderBase()")

    TelegramClient: Type[tgclient.client_types.TgmountTelegramClientReaderProto]
    MessageSource: Type[tgclient.MessageSourceSimple]
    FilesSource: Type[tgclient.TelegramFilesSource]
    FileFactory: Type[FileFactoryDefault]
    FilesSourceCaching: Type[cache.FilesSourceCaching]
    SourcesProvider: Type[SourcesProvider]
    TgmountBase = TgmountBase

    classifier: classifier.ClassifierBase
    caches: CachesProviderProto
    filters: FilterProviderProto
    wrappers: DirWrapperProviderProto
    producers: ProducersProviderBase

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

        message_sources, fetchers_dict = await self.create_messages_source_provider(
            client, file_factory, cfg
        )

        return TgmountResources(
            file_factory=file_factory,
            sources=message_sources,
            filters=self.filters.get_filters(),
            producers=self.producers,
            caches=cached_factories,
            wrappers=self.wrappers.get_wrappers(),
            classifier=self.classifier,
            vfs_wrappers={},
            fetchers_dict=fetchers_dict,
        )

    async def create_messages_source_provider(
        self,
        client: tgclient.client_types.TgmountTelegramClientReaderProto,
        file_factory: FileFactoryDefault,
        cfg: config.Config,
    ):
        sources_used_in_root = TgmountConfigReader().get_used_sources(cfg.root.content)

        message_source_dict = {
            k: self.MessageSource(
                # client,
                # ms.entity,
                # ms.limit,
                # receive_updates=none_fallback(ms.updates, True),
            )
            for k, ms in cfg.message_sources.sources.items()
            if k in sources_used_in_root
        }

        fetchers_dict = {
            k: {
                "source": message_source_dict[k],
                "config": ms,
                "fetcher": TelegramMessagesFetcher(client, ms),
                "updates": none_fallback(ms.updates, True),
            }
            for k, ms in cfg.message_sources.sources.items()
            if k in sources_used_in_root
        }

        for src in message_source_dict.values():
            src.filters.append(file_factory.supports)

        message_sources_provider = self.SourcesProvider(message_source_dict)

        return message_sources_provider, fetchers_dict

    async def create_tgmount(self, cfg: config.Config) -> TgmountBase:

        self.client = await self.create_client(cfg)
        self.resources = await self.create_resources(self.client, cfg)

        tgm = self.TgmountBase(
            client=self.client,
            resources=self.resources,
            root_config=cfg.root.content,
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

    async def create_vfs_tree(self):
        return VfsTree()
