from typing import Awaitable, Callable, Optional, Protocol, TypeVar

import telethon
from tgmount.cache.reader import CacheBlockReaderWriter
from tgmount.cache._storage.memory import CacheBlockStorageMemory
from .reader import CacheBlockReaderWriter
from .types import DocId

