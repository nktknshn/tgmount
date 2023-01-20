import argparse
import logging
import os
import sys
from collections.abc import Callable
from typing import Optional, TypedDict

from tgmount import cli
from tgmount import main as main_settings
from tgmount.cli.util import ClientEnv, get_tgapp_and_session

# import list_dialogs, list_documents, add_list_documents_arguments
from tgmount.main.util import run_main
from tgmount.tglog import init_logging
from tgmount.tgmount.error import TgmountError

"""
export TGAPP=111111:ac7e6350d04adeadbeedf1af778773d6f0 TGSESSION=tgfs

tgmount auth [session]
tgmount list dialogs
tgmount list documents [entity]
tgmount mount [config] [mount_path] 
"""


def get_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument("--session", type=str, required=False)
    parser.add_argument("--tgapp", type=str, required=False)
    parser.add_argument("--debug", default=False, action="store_true")

    commands_subparsers = parser.add_subparsers(dest="command")

    command_auth = commands_subparsers.add_parser("auth")
    command_mount = commands_subparsers.add_parser("mount")
    command_validate = commands_subparsers.add_parser("validate")
    command_stats = commands_subparsers.add_parser("stats")

    command_list = commands_subparsers.add_parser("list")
    command_list_subparsers = command_list.add_subparsers(dest="list_subcommand")
    command_list_dialogs = command_list_subparsers.add_parser("dialogs")
    command_list_documents = command_list_subparsers.add_parser("documents")

    cli.add_list_documents_arguments(command_list_documents)
    cli.add_mount_arguments(command_mount)
    cli.add_stats_parser(command_stats)

    return parser


async def main():

    args = get_parser().parse_args()

    init_logging(debug_level=logging.DEBUG if args.debug else logging.INFO)

    if args.command == "list" and args.list_subcommand == "dialogs":
        session, api_id, api_hash = get_tgapp_and_session(args)

        async with ClientEnv(session, api_id, api_hash) as client:
            await cli.list_dialogs(client)

    elif args.command == "list" and args.list_subcommand == "documents":
        session, api_id, api_hash = get_tgapp_and_session(args)
        async with ClientEnv(session, api_id, api_hash) as client:
            await cli.list_documents(
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

    elif args.command == "mount":
        session, api_id, api_hash = get_tgapp_and_session(args)
        main_settings.run_forever = args.run_server
        api_credentials = (
            (api_id, api_hash) if api_id is not None and api_hash is not None else None
        )
        await cli.mount(
            args.config,
            api_credentials=api_credentials,
            session=args.session,
            mount_dir=args.mount_dir,
            debug_fuse=args.debug_fuse,
            min_tasks=args.min_tasks,
            run_server=args.run_server,
            subfolder=args.subfolder,
        )

    elif args.command == "stats":
        await cli.stats(args)


if __name__ == "__main__":
    try:
        run_main(
            main,
            forever=main_settings.run_forever,
        )
    except TgmountError as e:
        print(f"Error happened: {e}")
