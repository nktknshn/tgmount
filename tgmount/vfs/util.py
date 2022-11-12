import asyncio
import os
from collections.abc import Callable
from typing import List
import logging


class MyLock(asyncio.Lock):
    def __init__(self, id: str, logger, level=logging.DEBUG):
        super(MyLock, self).__init__()
        self.id = id
        self.logger = logger
        self.level = level

    @property
    def state(self):
        return "locked" if self.locked() else "unlocked"

    async def acquire(self) -> bool:
        self.logger.log(
            self.level, f"{self.id}: + acquiring. Current state: {self.state}"
        )
        # traceback.print_stack()
        ret = await super(MyLock, self).acquire()
        self.logger.log(self.level, f"{self.id}: + locked")
        return ret

    def release(self) -> None:
        self.logger.log(self.level, f"{self.id}: - release")
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


""" 
assert norm_and_parse_path("/") == ["/"]
assert norm_and_parse_path("/a") == ["/", "a"]
assert norm_and_parse_path("a") == ["a"]
assert norm_and_parse_path("a/") == ["a"]
assert norm_and_parse_path("/a/") == ["/", "a"]
assert norm_and_parse_path("/a/b") == ["/", "a", "b"]
assert norm_and_parse_path("a/b") == ["a", "b"]
assert norm_and_parse_path("/a/b/") == ["/", "a", "b"]
assert norm_and_parse_path("/a/b/c") == ["/", "a", "b", "c"]
"""


def path_join(*paths: str):
    return os.path.join("/", *[path_remove_slash(p) for p in paths])


def path_remove_slash(path: str):
    if path.startswith("/"):
        return path[1:]

    return path


from functools import lru_cache


@lru_cache
def norm_path(p: str, addslash=False):
    if p == "":
        p = "/"

    p = os.path.normpath(p)

    if p.startswith("/") or not addslash:
        return p

    return "/" + p


def parent_path(p: str):
    return os.path.dirname(p)


def norm_and_parse_path(p: str, noslash=False):
    p = os.path.normpath(p)
    dirs = p.split(os.sep)
    if dirs[0] == "":
        dirs[0] = "/"
    if dirs[0] != "/":
        dirs = ["/", *dirs]
    if dirs[-1] == "":
        del dirs[-1]

    if p.startswith("/") and not noslash:
        return dirs

    return dirs[1:]


napp = norm_and_parse_path


def nappb(path: str, encoding: str = "utf-8", noslash=False) -> list[bytes]:
    lpath = norm_and_parse_path(path, noslash)

    return [p.encode(encoding) for p in lpath]


@lru_cache
def split_path(path: str, addslash=False):
    """Splits path into parent and child normalizing parent path optionally adding leading slash"""
    head, tail = os.path.split(path)

    return norm_path(head, addslash), tail
