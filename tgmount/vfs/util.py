import asyncio
import os
from collections.abc import Callable
from typing import List


class MyLock(asyncio.Lock):
    def __init__(self, id: str, logger):
        super(MyLock, self).__init__()
        self.id = id
        self.logger = logger

    async def acquire(self) -> bool:
        self.logger.debug(f"{self.id}: + acquiring. Current state: {self.locked()}")
        # traceback.print_stack()
        ret = await super(MyLock, self).acquire()
        self.logger.debug(f"{self.id}: + locked")
        return ret

    def release(self) -> None:
        self.logger.debug(f"{self.id}: - release")
        # logger.debug('waiters: %s', str(self._waiters))
        # traceback.print_stack()
        super(MyLock, self).release()


def lazy_list_from_thunk(content_thunk: Callable[[], List]):
    content = []

    def _inner():
        if not content:
            content.extend(content_thunk())
        return content

    async def f(off):
        return _inner()[off:]

    return f


# see test_util.py
def norm_and_parse_path(p: str):
    p = os.path.normpath(p)
    dirs = p.split(os.sep)
    if dirs[0] == "":
        dirs[0] = "/"
    if dirs[0] != "/":
        dirs = ["/", *dirs]
    if dirs[-1] == "":
        del dirs[-1]

    if p.startswith("/"):
        return dirs

    return dirs[1:]


napp = norm_and_parse_path


def nappb(path: str, encoding: str = "utf-8") -> list[bytes]:
    lpath = norm_and_parse_path(path)

    return [p.encode(encoding) for p in lpath]
