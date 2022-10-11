import abc
from typing import Iterable, Mapping, Set

import pathvalidate
import telethon
from telethon.tl.custom import Message
from tgmount import tglog, zip as z
from tgmount.tgclient.message_source import MessageSourceSimple, MessagesSet
from tgmount.tgmount.error import TgmountError
from tgmount.tgmount.vfs_tree_producer_types import (
    ProducerConfig,
    VfsStructureConfig,
    VfsTreeProducerProto,
)
from tgmount.util.col import sets_difference
from tgmount.util.tg import get_entity_type_str

from .grouperbase import GroupedMessages, VfsTreeProducerGrouperBase


class VfsTreeProducerZipsAsDirs(VfsTreeProducerProto):
    pass
