from typing import Dict, Generic, Tuple, Any, Optional, TypeVar


T = TypeVar("T")


class FileSystemHandles(Generic[T]):
    """Stores mapping from fh to a tuple of item and handle object"""

    LAST_FH = 10

    def __init__(self, last_fh=None):
        self._fhs: Dict[int, Tuple[T, Any]] = {}
        self._fh_by_item: Dict[T, int] = {}

        self._last_fh = last_fh if last_fh is not None else FileSystemHandles.LAST_FH

    def stats(self) -> str:
        return str(self._fh_by_item)

    def get_handles(self):
        return list(self._fhs.keys())

    def get_by_item(self, item: T) -> int | None:
        return self._fh_by_item.get(item)

    def open_fh(self, item: T, data=None):
        fh = self._new_fh()
        self._fhs[fh] = item, data
        self._fh_by_item[item] = fh
        return fh

    def get_by_fh(self, fh: int) -> Tuple[Optional[T], Optional[Any]]:
        item = self._fhs.get(fh)

        if item is None:
            return None, None

        return item

    def release_fh(self, fh: int):
        if fh in self._fhs:
            item, handle = self._fhs[fh]
            del self._fhs[fh]
            del self._fh_by_item[item]

    def _new_fh(self):
        self._last_fh += 1
        return self._last_fh
