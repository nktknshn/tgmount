#!/usr/bin/env python3

import asyncio
import json
import logging
import os
import socket
import sys
from argparse import ArgumentParser
from typing import List

import pyfuse3
import pyfuse3_asyncio
import socks
from telethon import events
from telethon.tl import types
from telethon.tl.custom.dialog import Dialog
from telethon.utils import get_display_name
from tqdm import tqdm

from tgmount.functions import download, list_dialogs, list_documents, mount
from tgmount.tgclient import TelegramFsClient
from tgmount.tgvfs import TelegramFsAsync
from tgmount.util import (DateTimeEncoder, document_to_dict, int_or_string,
                          none_or_int)

unmount_required = False


async def main():

    global unmount_required

    api_id = None
    api_hash = None

    proxy = None

    if 'TGAPP' in os.environ:
        [api, hash] = os.environ['TGAPP'].split(":")

        api_id = int(api)
        api_hash = hash

    if api_id is None or api_hash is None:
        print("Use TGAPP environment variable to set up telegram app API credentials")
        print("Obtain your API credentials at https://my.telegram.org/apps")
        sys.exit(1)

    [args_parser, options] = parse_args()

    init_logging(options.debug)

    logging.debug(options)

    proxy = options.socks

    async def client():
        client = TelegramFsClient(options.session, api_id, api_hash, proxy)
        await client.auth()
        return client

    if options.list_dialogs:
        await list_dialogs(await client(),
                           limit=none_or_int(options.limit),
                           json_output=options.json,
                           offset_id=int_or_string(options.offset_id))

    elif options.list_documents:
        await list_documents(await client(),
                             id=int_or_string(options.id),
                             offset_id=int(options.offset_id),
                             limit=none_or_int(options.limit),
                             reverse=options.reverse,
                             json_output=options.json,
                             filter_music=not options.all_files)

    elif options.mount:
        unmount_required = True
        await mount(await client(),
                    id=int_or_string(options.id),
                    destination=options.mount,
                    offset_id=int(options.offset_id),
                    limit=none_or_int(options.limit),
                    filter_music=not options.all_files,
                    debug_fuse=options.debug_fuse,
                    reverse=options.reverse,
                    updates=not options.no_updates,
                    fsname=options.fsname)

    elif options.download:
        await download(await client(),
                       id=int_or_string(options.id),
                       destination=options.download,
                       files=[int(id) for id in options.files.split(',')])
    else:
        args_parser.print_help()


def proxy_arg(value):
    [proxy_host, proxy_port] = value.split(':')
    return (socks.SOCKS5, proxy_host, int(proxy_port))


def parse_args():
    '''Parse command line'''

    parser = ArgumentParser()

    parser.add_argument('--id', default=None,
                        required='--mount' in sys.argv
                        or '--list-documents' in sys.argv
                        or '--download' in sys.argv,
                        help='chat or channel ID. Telegram username or numeric ID')

    #  actions
    parser.add_argument('--mount', type=str, metavar='DIR',
                        help='mount to DIR')

    parser.add_argument('--list-dialogs', default=False, action="store_true",
                        help='print available telegram dialogs')

    parser.add_argument('--list-documents', action='store_true', default=False,
                        help='print available documents')

    parser.add_argument('--download', type=str, metavar='DIR',
                        help='save files to DIR. Use with --files parameter')

    # parametres
    parser.add_argument('--files',
                        # action='store_true',
                        required='--download' in sys.argv,
                        default=[],
                        help='comma separated list of document IDs')

    parser.add_argument('--all-files', action='store_true', default=False,
                        help='Retrieve all type of files, not only audio files. Default: no')

    parser.add_argument('--no-updates', action='store_true', default=False,
                        help='don\'t listen for new files. Default: no')

    parser.add_argument('--reverse', action='store_true', default=False,
                        help='documents will be searched in reverse order (from oldest to newest). Default: from newest to oldest')

    parser.add_argument('--limit', default=None,
                        type=int,
                        help='limit number of documents or dialogs. default: unlimited')

    parser.add_argument('--offset-id',
                        type=int,
                        default=0,
                        help='offset message ID. Only documents previous to the given ID will be retrieved')

    # misc

    parser.add_argument('--session', type=str, default="tgfs",
                        help='telegram session name. Default: tgfs')

    parser.add_argument('--fsname', type=str, default="tgfs",
                        help='VFS name. Default: tgfs')

    parser.add_argument('--socks', default=None,
                        help='SOCKS5 proxy i.e. 127.0.0.1:9050', type=proxy_arg)

    parser.add_argument('--debug', action='store_true', default=False,
                        help='enable debugging output')

    parser.add_argument('--debug-fuse', action='store_true', default=False,
                        help='enable FUSE debugging output')

    parser.add_argument('--json', action='store_true', default=False,
                        help='json output. Default: no')

    return [parser, parser.parse_args()]


def init_logging(debug=False):

    formatter = logging.Formatter(
        '%(levelname)s\t[%(name)s]\t%(message)s', datefmt="%Y-%m-%d %H:%M:%S")

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()

    if (root_logger.hasHandlers()):
        root_logger.handlers.clear()

    root_logger.addHandler(handler)

    if debug:
        handler.setLevel(logging.DEBUG)
        root_logger.setLevel(logging.DEBUG)
        logging.getLogger('tgvfs').setLevel(logging.DEBUG)
        logging.getLogger('tgclient').setLevel(logging.DEBUG)
        logging.getLogger('telethon').setLevel(logging.INFO)
    else:
        handler.setLevel(logging.INFO)
        root_logger.setLevel(logging.INFO)
        logging.getLogger('tgvfs').setLevel(logging.INFO)
        logging.getLogger('tgclient').setLevel(logging.INFO)
        logging.getLogger('telethon').setLevel(logging.ERROR)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Bye")
    finally:
        if unmount_required:
            pyfuse3.close(unmount=True)
