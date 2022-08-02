'''
pyfuse3_asyncio.py

asyncio compatibility layer for pyfuse3

Copyright © 2018 Nikolaus Rath <Nikolaus.org>
Copyright © 2018 JustAnotherArchivist

This file is part of pyfuse3. This work may be distributed under
the terms of the GNU LGPL.
'''

import asyncio
import logging
import sys

import greenback
import pyfuse3

# from easy_vfs.util import MyLock

logger = logging.getLogger('tgvfs')
# Lock = lambda: MyLock('greenback_log', logger)
Lock = asyncio.Lock


# logger = logging.getLogger('tgvfs')


def enable():
    '''Switch pyfuse3 to asyncio mode.'''

    fake_trio = sys.modules['tgmount.vfs.greenback.pyfuse3_asyncio_greenback']
    fake_trio.lowlevel = fake_trio  # type: ignore
    fake_trio.from_thread = fake_trio  # type: ignore
    pyfuse3.trio = fake_trio


def disable():
    '''Switch pyfuse3 to default (trio) mode.'''

    pyfuse3.trio = sys.modules['trio']


def current_trio_token() -> str:
    return 'asyncio'
    # return 'pyfuse3_asyncio_greenback'


async def wait_readable(fd):
    future = asyncio.Future()
    loop = asyncio.get_event_loop()
    loop.add_reader(fd, future.set_result, None)
    future.add_done_callback(lambda f: loop.remove_reader(fd))
    await future


def current_task():
    if sys.version_info < (3, 7):
        return asyncio.Task.current_task()
    else:
        return asyncio.current_task()


class _Nursery:
    async def __aenter__(self):
        self.tasks = set()
        return self

    def start_soon(self, func, *args, name=None):
        if sys.version_info < (3, 7):
            task = asyncio.ensure_future(func(*args))
        else:
            task = asyncio.create_task(func(*args))

        # greenback.bestow_portal(task)
        task.set_name(name)
        self.tasks.add(task)

    async def __aexit__(self, exc_type, exc_value, traceback):
        logger.debug('exiting')
        # Wait for tasks to finish
        while len(self.tasks):
            # Create a copy of the task list to ensure that it's not a problem
            # when self.tasks is modified
            done, pending = await asyncio.wait(tuple(self.tasks))
            for task in done:
                self.tasks.discard(task)

            # We waited for ALL_COMPLETED (default value of 'when' arg to
            # asyncio.wait), so all tasks should be completed. If that's not the
            # case, something's seriously wrong.
            assert len(pending) == 0


def open_nursery():
    return _Nursery()
