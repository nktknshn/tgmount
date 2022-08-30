import asyncio
import os
import tempfile
import json
from tgmount import tgmount
from tgmount.tgmount import Tgmount

SOCKET_DIR = tempfile.gettempdir()
SOCKET_FILE_NAME = "tgmount.socket"
SOCKET_FILE = os.path.join(SOCKET_DIR, SOCKET_FILE_NAME)


# class BigIntEncoder(json.JSONEncoder):
#     def default(self, inp):
#         if isinstance(inp, int) and inp > 9007199254740992:
#             return str(inp)

#         return super().encode(inp)


class ControlServer:
    def __init__(self, tgmount: Tgmount, socket_file=SOCKET_FILE) -> None:
        self._socket_file = socket_file
        self._server: asyncio.Server
        self._tgmount = tgmount

    async def accept_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ):

        info = {}

        if self._tgmount.fs is not None:
            info["fs"] = {}

            info["fs"]["inodes"] = self._tgmount.fs.inodes.get_inodes_with_paths_str()
            info["fs"]["handles"] = self._tgmount.fs.handles.get_handles()
            info["fs"]["tree"] = self._tgmount.fs.get_inodes_tree()

        info["caches"] = {}

        for k, v in self._tgmount.caches.items():
            total_stored = await v.total_stored()

            info["caches"][k] = {}
            info["caches"][k]["total_stored"] = total_stored

        writer.write(json.dumps(info).encode("utf-8"))
        writer.close()

    async def start(self):
        self._server = await asyncio.start_unix_server(
            self.accept_connection,
            self._socket_file,
        )
