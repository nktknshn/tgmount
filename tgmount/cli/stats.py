from argparse import ArgumentParser, Namespace
from typing import Optional
from .logger import logger
from tgmount.controlserver.server import ControlServer, SOCKET_FILE
import asyncio
import os
import tempfile
import json
from tgmount import main


def print_output(obj, func, print_json=False):
    if print_json:
        print(json.dumps(obj))
    else:
        func(obj)


def print_inodes(inodes: list[tuple[int, list[str]]]):
    for inode, path_list in inodes:
        print(f"{inode}\t{os.path.join(*path_list)}")


async def stats(args: Namespace):
    reader, writer = await asyncio.open_unix_connection(args.socket_file)
    data = await reader.read()
    data_dict = json.loads(data)

    if args.stats_subcommand == "inodes":
        print_output(data_dict["fs"]["inodes"], print_inodes, print_json=args.json)

    elif args.stats_subcommand == "inodes-tree":
        print_output(data_dict["fs"]["tree"], None, print_json=args.json)

    writer.close()


def add_stats_parser(command_stats: ArgumentParser):

    command_stats.add_argument("--socket-file", type=str, default=SOCKET_FILE)

    command_stats_subparsers = command_stats.add_subparsers(dest="stats_subcommand")

    command_stats_inodes = command_stats_subparsers.add_parser("inodes")

    command_stats_inodes.add_argument(
        "--paths", "-p", action="store_true", default=False
    )

    command_stats_inodes.add_argument("--json", action="store_true", default=False)

    command_stats_inodes_tree = command_stats_subparsers.add_parser("inodes-tree")
    command_stats_inodes_tree.add_argument("--json", action="store_true", default=False)
