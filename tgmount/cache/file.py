import logging
import os
from typing import IO, Dict, Optional, Protocol, Set

import aiofiles
from aiofiles.threadpool.binary import AsyncBufferedReader
from tgmount.vfs.util import MyLock

from .types import CacheBlocksStorageProto

logger = logging.getLogger("tgmount-cache")


class CacheBlockStorageFile(CacheBlocksStorageProto):
    def __init__(self, f: AsyncBufferedReader):
        self.file = f

        self.total_size: Optional[int] = None
        self.blocksize: Optional[int] = None
        self.blocks_number: Optional[int] = None
        self.blocks_flags: Optional[int] = None

        self._lock = MyLock("FileCacheBlockStorage.lock", logger)

    @staticmethod
    async def open_cache_file(fpath: str):
        print("open_cache_file")
        # try:
        #     async with aiofiles.open(fpath, 'r') as f:
        #         return FileCacheBlockStorageComplete(f, blocksize)
        # except OSError:
        partial_file_name = f"{fpath}.partial"
        data = await aiofiles.open(partial_file_name, "r+b")
        f = CacheBlockStorageFile(data)
        await f.read_headers()
        return f

    @staticmethod
    async def create_cache_file(fpath: str, *, size: int, blocksize: int):
        logger.log(logging.DEBUG, "create_cache_file")

        partial_file_name = f"{fpath}.partial"
        f = await aiofiles.open(partial_file_name, "w+b")
        await f.write(create_initial_header(size, blocksize))
        await f.write(b"\x00" * size)
        await f.close()

    async def get(self, block_number: int) -> Optional[bytes]:
        async with self._lock:
            return await self._get_block(block_number)

    async def put(self, block_number: int, block: bytes):
        async with self._lock:
            await self._put_block(block_number, block)

    async def blocks(self):
        if self.blocks_number is None or self.blocks_flags is None:
            return

        return set(get_complete_blocks(self.blocks_number, self.blocks_flags))

    async def read_headers(self):
        (
            self.total_size,
            self.blocksize,
            self.blocks_number,
            self.blocks_flags,
        ) = await read_cache_file_headers(self.file)

        print(
            f"self.size={self.total_size} self.blocksize={self.blocksize} self.blocks_number={self.blocks_number} "
            f"flags_len={flags_len(self.blocks_number)} self.blocks_flags={self.blocks_flags}"
        )

        print(f"is_complete={self.is_complete}")

    @property
    def is_complete(self):
        if self.blocks_number is None:
            return False

        return self.blocks() == set(range(0, self.blocks_number))

    async def close(self):
        await self.file.close()

    async def _put_block(self, block_number: int, block: bytes):
        print(f"put_block(block_number={block_number})")
        await self._seek_to_block(block_number)
        await self.file.write(block)
        await self.file.flush()
        await self._update_flag(block_number)

    async def _get_block(self, block_number: int) -> Optional[bytes]:

        if self.blocksize is None:
            return

        if self._get_flag(block_number):
            await self._seek_to_block(block_number)
            return await self.file.read(self.blocksize)
        else:
            return None

    def _get_flag(self, block_number) -> bool:
        return self.blocks_flags >> block_number & 1

    async def _update_flag(self, block_number: int, fetched: bool = True):

        if self.blocks_flags is None:
            return

        if fetched:
            self.blocks_flags |= 1 << block_number
        else:
            self.blocks_flags &= ~1 << block_number

        await self._save_flags()

    async def _save_flags(self):
        if self.blocks_flags is None or self.blocks_number is None:
            return

        await self._seek_to_flags()
        await self.file.write(
            self.blocks_flags.to_bytes(flags_len(self.blocks_number), byteorder="big")
        )
        await self.file.flush()

    async def _seek_to_flags(self):
        await self.file.seek(12, os.SEEK_SET)

    async def _seek_to_block(self, block_number: int):
        if self.blocksize is None or self.blocks_number is None:
            return

        await self.file.seek(
            12 + flags_len(self.blocks_number) + self.blocksize * block_number,
            os.SEEK_SET,
        )


class FileCacheComplete(CacheBlocksStorageProto):
    def __init__(self, f: AsyncBufferedReader, size: int, blocksize: int):
        self.file = f
        self.blocksize = blocksize
        self.total_size = size

    async def get(self, block_number: int) -> Optional[bytes]:
        await self._seek_to_block(block_number)
        return await self.file.read(self.blocksize)

    async def put(self, block_number: int, block: bytes):
        logger.error("putting into a complete file")
        pass

    async def blocks(self) -> Set[int]:
        return set(range(0, get_blocks_number(self.total_size, self.blocksize)))

    async def _seek_to_block(self, block_number: int):
        await self.file.seek(self.blocksize * block_number, os.SEEK_SET)


def flags_len(blocks_number: int):
    bits_n = blocks_number + 8 - blocks_number % 8
    return bits_n // 8


def get_blocks_number(size: int, blocksize: int):
    return size // blocksize + 1


def create_initial_header(size: int, blocksize: int):
    blocks_number = size // blocksize + 1
    bytes_n = flags_len(blocks_number)

    check_bytes = int("0x07070707", 16).to_bytes(4, byteorder="big")
    blocksize_bytes = blocksize.to_bytes(4, byteorder="big")
    blocks_number_bytes = blocks_number.to_bytes(4, byteorder="big")
    flags_bytes = (0).to_bytes(bytes_n, byteorder="big")

    return check_bytes + blocksize_bytes + blocks_number_bytes + flags_bytes


async def read_cache_file_headers(f):
    await f.seek(0, os.SEEK_END)
    cache_file_size = await f.tell()

    await f.seek(0, os.SEEK_SET)

    if not cache_file_size:
        raise RuntimeError("Empty file")

    check_bytes = await f.read(4)

    if not int.from_bytes(check_bytes, "big") == int("0x07070707", 16):
        raise RuntimeError("wrong check bytes")

    blocksize = int.from_bytes(await f.read(4), "big")
    blocks_number = int.from_bytes(await f.read(4), "big")
    flags_length = flags_len(blocks_number)
    blocks_flags = await f.read(flags_length)

    size = cache_file_size - 12 - flags_length
    return size, blocksize, blocks_number, int.from_bytes(blocks_flags, "big")


async def create_cache_file(fpath: str, *, size: int, blocksize: int):
    print("create_cache_file")
    async with aiofiles.open(fpath, "wb") as f:
        await f.write(create_initial_header(size, blocksize))
        await f.write(b"\x00" * size)


def is_complete(blocks_number: int, blocks_flags: int):
    complete_flags_bytes = int("" + "1" * blocks_number, 2)
    return complete_flags_bytes == blocks_flags


def get_complete_blocks(blocks_number: int, blocks_flags: int):
    for b in range(0, blocks_number):
        if blocks_flags >> b & 1:
            yield b


async def try_open_file(fpath: str, mode="rb") -> Optional[IO[bytes]]:
    try:
        f = await aiofiles.open(fpath, mode)  # type: ignore
    except OSError:
        return None
    except Exception as e:
        print(e)
        return None

    return f
