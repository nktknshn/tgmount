import os
import sys
import argparse
from typing import Optional, TypedDict
from tgmount.tgclient import TgmountTelegramClient
from tgmount.tgmount import TgmountError
from tgmount.cli.util import read_os_env, parse_tgapp_str
from tgmount.cli import list_dialogs, list_documents, add_list_documents_arguments
from tgmount.main.util import run_main

"""
export TGAPP=111111:ac7e6350d04adeadbeedf1af778773d6f0
export TGSESSION=tgfs

tgmount auth [session]
tgmount list dialogs
tgmount list documents [entity]
tgmount mount [config] [mount_path] 
"""


def get_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument("--session", type=str, required=False)
    parser.add_argument("--tgapp", type=str, required=False)

    commands_subparsers = parser.add_subparsers(dest="command")

    command_list = commands_subparsers.add_parser("list")

    command_list_subparsers = command_list.add_subparsers(dest="list_subcommand")

    command_list_dialogs = command_list_subparsers.add_parser("dialogs")
    command_list_documents = command_list_subparsers.add_parser("documents")

    add_list_documents_arguments(command_list_documents)

    return parser


def get_client(session: str, api_id: int, api_hash: str):
    return TgmountTelegramClient(session, api_id, api_hash)


def get_tgapp_and_session(args: argparse.Namespace):
    os_env = read_os_env()

    api_id = os_env["api_id"]
    api_hash = os_env["api_hash"]
    session = os_env["session"]

    if args.tgapp is not None:
        api_id, api_hash = parse_tgapp_str(args.tgapp)

    if args.session is not None:
        session = args.session

    if session is None or api_id is None or api_hash is None:
        raise TgmountError(f"missing either session or api_id or api_hash")

    return session, api_id, api_hash


async def main():

    args = get_parser().parse_args()

    # print(args)

    session, api_id, api_hash = get_tgapp_and_session(args)
    client = get_client(session, api_id, api_hash)

    await client.auth()

    try:
        if args.command == "list" and args.list_subcommand == "dialogs":
            await list_dialogs(client)
        elif args.command == "list" and args.list_subcommand == "documents":
            await list_documents(
                client,
                args.entity,
                limit=args.limit,
                reverse=args.reverse,
                print_message_object=args.print_message_object,
                include_unsupported=args.include_unsupported,
                only_unsupported=args.only_unsupported,
                print_all_matching_types=args.print_all_matching_types,
                only_unique_docs=args.only_unique_docs,
            )
    finally:
        if cor := client.disconnect():
            await cor


if __name__ == "__main__":
    run_main(main, unmount=False)
