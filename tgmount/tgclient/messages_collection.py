import logging
from abc import abstractmethod
from typing import (
    Any,
    Generic,
    Iterable,
    OrderedDict,
    Protocol,
    Sequence,
    TypeGuard,
    TypeVar,
    Union,
)

from tgmount.util.col import sets_difference

from .logger import logger as _logger


class WithId(Protocol):
    id: int


M = TypeVar("M", bound=WithId)


def messages_difference(
    before: Sequence[M], after: Sequence[M]
) -> tuple[list[M], list[M], list[tuple[M, M]],]:
    before_dict = {m.id: m for m in before}
    after_dict = {m.id: m for m in after}

    removed, new, common = sets_difference(
        set(before_dict.keys()), set(after_dict.keys())
    )

    return (
        [before_dict[i] for i in removed],
        [after_dict[i] for i in new],
        list(
            zip(
                [before_dict[i] for i in common],
                [after_dict[i] for i in common],
            )
        ),
    )


class MessagesCollection(Generic[M]):
    logger = _logger.getChild("MessagesCollection")
    logger.setLevel(logging.CRITICAL)

    @staticmethod
    def aa():
        pass

    @staticmethod
    def from_iterable(it: Iterable[M]):
        col = MessagesCollection()
        col.add_messages(it)
        return col

    def __init__(self) -> None:
        self._messages: OrderedDict[int, M] = OrderedDict()

    def _item_hash(self, m: M):
        return m.id

    def add_message(self, m: M, overwright=False) -> M | None:
        h = self._item_hash(m)

        if not overwright and h in self._messages:
            self.logger.warn(f"{m} is already in the collection")
            return

        self._messages[h] = m
        return m

    def add_messages(self, ms: Iterable[M], overwright=False):
        res = []
        for m in ms:
            if self.add_message(m, overwright=overwright) is not None:
                res.append(m)
        return res

    def remove_ids(self, ids: Iterable[int]) -> list[M]:
        res = []
        for i in ids:
            try:
                removed = self._messages.pop(i)
            except KeyError:
                self.logger.warn(f"KeyError: {i} is not in the collection")
            else:
                res.append(removed)
        return res

    def remove_messages(self, ms: Iterable[M]) -> list[M]:
        res = []
        for m in ms:
            h = self._item_hash(m)
            try:
                del self._messages[h]
            except KeyError:
                self.logger.warn(f"KeyError: {m} is not in the collection")
            else:
                res.append(m)
        return res

    def get_difference(self, ms: Iterable[M]):
        return messages_difference(self.get_messages_list(), list(ms))
        # removed = []
        # new = []
        # common = []

        # ms_dict = {m.id: m for m in ms}

        # removed, new, common = sets_difference(
        #     set(self._messages.keys()), set(ms_dict.keys())
        # )

        # return (
        #     [self._messages[i] for i in removed],
        #     [ms_dict[i] for i in new],
        #     [self._messages[i] for i in common],
        # )

    def get_messages_iter(self):
        return self._messages.values()

    def get_messages_list(self):
        return list(self._messages.values())

    def get_by_ids(self, ids: list[int]):
        try:
            return [self._messages[i] for i in ids]
        except KeyError:
            return None

    def __len__(self):
        return len(self._messages)

    def __iter__(self):
        return iter(self._messages.values())
