#!/usr/bin/env python3

import asyncio
import logging
import os
import sys
import traceback
from argparse import ArgumentParser

import pyfuse3

from tgmount.actions import download, list_dialogs, list_documents, mount
from tgmount.logging import init_logging
from tgmount.tgclient import TelegramFsClient
from tgmount.util import (int_or_string, none_or_int, proxy_arg)

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
        print("Use TGAPP environment variable to set up telegram app API id")
        print("Obtain your API credentials at https://my.telegram.org/apps")
        sys.exit(1)

    [args_parser, options] = parse_args()

    init_logging(options.debug)

    logging.debug(options)

    proxy = options.socks

    async def client():
        client = TelegramFsClient(options.session, api_id, api_hash, proxy, options.ipv6)
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
                    fsname=options.fsname,
                    additional_fuse_options=options.fuse_options,
                    new_file_webhook_urls=options.new_file_webhook_url)

    elif options.download:
        await download(await client(),
                       id=int_or_string(options.id),
                       destination=options.download,
                       files=[int(id) for id in options.files.split(',')])
    else:
        args_parser.print_help()


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

    parser.add_argument('--ipv6', action='store_true', default=False,
                        help='enable IPv6')

    parser.add_argument('--debug', action='store_true', default=False,
                        help='enable debugging output')

    parser.add_argument('--debug-fuse', action='store_true', default=False,
                        help='enable FUSE debugging output')

    parser.add_argument('--json', action='store_true', default=False,
                        help='json output. Default: no')

    parser.add_argument('--fuse-options', action='append', default=None,
                        help='pass FUSE options to FUSE when mounting', type=str)

    parser.add_argument('--new-file-webhook-url', action='append', default=None,
                        help='send request to this URL when new file appears', type=str)

    return [parser, parser.parse_args()]


if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Bye")
    except Exception:
        print(traceback.format_exc())
    finally:
        if unmount_required:
            pyfuse3.close(unmount=True)
