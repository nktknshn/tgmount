import abc
from typing import Mapping, Type

from telethon.tl.custom import Message

from tgmount import cache, config, tg_vfs, tgclient
from tgmount.tg_vfs import classifier
from tgmount.tgclient import TgmountTelegramClient
from tgmount.tgmount.producers import TreeProducersProviderProto

from .caches import CachesProviderProto
from .filters import FilterProviderProto
from .tgmountbase import Tgmount
from .types import TgmountRoot
from .wrappers import DirWrapperProviderProto
from .tgmount_root import tgmount_root


class TgmountBuilderBase(abc.ABC):
    TelegramClient: Type[tgclient.TgmountTelegramClient]
    MessageSource: Type[tgclient.TelegramMessageSource]
    FilesSource: Type[tgclient.TelegramFilesSource]
    FileFactory: Type[tg_vfs.FileFactoryDefault]
    FilesSourceCaching: Type[cache.FilesSourceCaching]

    classifier: classifier.ClassifierBase
    caches: CachesProviderProto
    filters: FilterProviderProto
    wrappers: DirWrapperProviderProto
    producers: TreeProducersProviderProto

    async def create_tgmount(self, cfg: config.Config) -> Tgmount:
        client = await self.create_client(cfg)

        messssage_sources = {
            k: await self.create_message_source(client, ms)
            for k, ms in cfg.message_sources.sources.items()
        }

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

        tgm = Tgmount(
            client=client,
            file_factory=file_factory,
            filters=self.filters.get_filters(),
            producers=self.producers.get_producers(),
            message_sources=messssage_sources,
            mount_dir=cfg.mount_dir,
            wrappers=self.wrappers.get_wrappers(),
            caches=caches,
            cached_sources=cached_factories,
            root=self.parse_root_dict(cfg.root.content),
            classifier=self.classifier,
        )

        for k, v in messssage_sources.items():
            v.subscribe(tgm.update)

        return tgm

    async def create_message_source(
        self,
        client: tgclient.TgmountTelegramClient,
        ms: config.MessageSource,
    ) -> tgclient.TelegramMessageSource:
        return self.MessageSource(client, ms.entity, ms.limit)

    async def create_client(self, cfg: config.Config):
        return self.TelegramClient(
            cfg.client.session,
            cfg.client.api_id,
            cfg.client.api_hash,
        )

    async def create_cache(
        self, client: TgmountTelegramClient, cache_config: config.Cache
    ):
        cache_factory_cls = await self.caches.get_cache_factory(cache_config.type)
        return cache_factory_cls(**cache_config.kwargs)

    def parse_root_dict(self, d: dict) -> TgmountRoot:
        return lambda resources: tgmount_root(d, resources=resources)
