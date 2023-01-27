from abc import abstractmethod
from typing import Generic, Mapping, Protocol, Type, TypeVar
from tgmount.cache.source import FilesSourceCached
from tgmount.cache.types import CacheProto
from tgmount.tgclient.client_types import TgmountTelegramClientReaderProto
from tgmount.tgclient.files_source import TelegramFilesSource
from tgmount.tgmount.error import TgmountError
from tgmount.tgmount.file_factory.filefactory import FileFactoryDefault

from tgmount.tgmount.file_factory.types import FileFactoryProto
from tgmount.tgmount.providers.provider_caches import CachesTypesProviderProto

from .logger import logger as module_logger

T = TypeVar("T", covariant=True)


class CacheFileFactoryFactoryProto(Protocol, Generic[T]):
    @abstractmethod
    async def create_cached_filefactory(
        self, cache_id: str, cache_type: str, cache_kwargs: Mapping
    ) -> FileFactoryProto:
        pass

    @abstractmethod
    def get_cache_by_id(self, cache_id: str) -> CacheProto | None:
        ...

    @abstractmethod
    def get_filesource_by_id(self, cache_id: str) -> FilesSourceCached | None:
        ...

    @abstractmethod
    def get_filefactory_by_id(self, cache_id: str) -> FileFactoryDefault | None:
        ...


class CacheFileFactoryFactory(CacheFileFactoryFactoryProto):
    FilesSource: Type[FilesSourceCached] = FilesSourceCached
    FileFactory: Type[FileFactoryDefault] = FileFactoryDefault
    logger = module_logger.getChild(f"CacheFileFactoryFactory")

    def __init__(
        self,
        client: TgmountTelegramClientReaderProto,
        caches_class_provider: CachesTypesProviderProto,
    ):
        self._client = client
        self._cache_classes_provider = caches_class_provider

        self._caches: dict[str, CacheProto] = {}
        self._caches_file_source: dict[str, FilesSourceCached] = {}
        self._caches_filefactories: dict[str, FileFactoryDefault] = {}

    def get_cache_by_id(self, cache_id: str) -> CacheProto | None:
        return self._caches.get(cache_id)

    def get_filesource_by_id(self, cache_id: str) -> FilesSourceCached | None:
        return self._caches_file_source.get(cache_id)

    def get_filefactory_by_id(self, cache_id: str) -> FileFactoryDefault | None:
        return self._caches_filefactories.get(cache_id)

    async def create_cached_filefactory(
        self, cache_id: str, cache_type: str, cache_kwargs: Mapping
    ) -> FileFactoryProto:

        self.logger.debug(
            f"create_cached_filefactory({cache_id}, {cache_type}, {cache_kwargs})"
        )

        cache_class = self._cache_classes_provider.get_cache_type(cache_type)

        if cache_class is None:
            raise TgmountError(f"Missing {cache_type} in cache provider.")

        cache = await cache_class.create(**cache_kwargs)

        assert cache_id not in self._caches

        fsc = self.FilesSource(self._client, cache=cache)
        fc = self.FileFactory(fsc)

        self._caches[cache_id] = cache
        self._caches_file_source[cache_id] = fsc
        self._caches_filefactories[cache_id] = fc

        return fc
