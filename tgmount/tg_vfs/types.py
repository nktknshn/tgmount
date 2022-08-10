from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable, Optional, Protocol

import pyfuse3
import telethon
from telethon.tl.custom.file import File
from tgmount import vfs

InputSourceItem = telethon.types.Photo | telethon.types.Document
