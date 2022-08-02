from typing import Dict, Generic, Tuple, Any, Optional, TypeVar


T = TypeVar("T")


class FileSystemHandlers(Generic[T]):
    def __init__(self):
        self._fhs: Dict[int, Tuple[T, Any]] = {}
        self._last_fh = 10

    def open_fh(self, item: T, data=None):
        fh = self._new_fh()
        self._fhs[fh] = item, data
        return fh

    def get_by_fh(self, fh: int) -> Tuple[Optional[T], Optional[Any]]:

        # if fh not in self._fhs:
        #     return None, None

        item = self._fhs.get(fh)

        if item is None:
            return None, None

        return item

    def release_fh(self, fh: int):
        if fh in self._fhs:
            del self._fhs[fh]

    def _new_fh(self):
        self._last_fh += 1
        return self._last_fh
