import dataclasses
import json
import logging
from typing import List

import pyfuse3
import pyfuse3_asyncio
from telethon.tl import types
from telethon.utils import get_display_name
from tqdm import tqdm

from .tgclient import TelegramFsClient
from .tgvfs import TelegramFsAsync
from .util import DateTimeEncoder


async def list_dialogs(client: TelegramFsClient, limit=None, json_output=False, offset_id=0):
    dialogs = await client.get_dialogs_dict(limit=limit, offset_id=offset_id)

    result = [{
        'name': name,
        'id': dialog.id,
    } for name, dialog in dialogs.items()]

    if json_output:
        print(json.dumps(result))
    else:
        for d in result:
            print("%s\t%s" % (d['id'], d['name']))


async def list_documents(client, id, offset_id: int = 0, limit: int = None,
                         filter_music=False, reverse=False, json_output=False):
    logging.debug("list_documents(id=%s, offset_id=%s, limit=%s)" %
                  (id, offset_id, limit))
    logging.debug("Querying entity %s(%s)" % (type(id), id))

    entity = await client.get_entity(id)

    logging.debug("Querying documents")

    messages, documents_handles = await client.get_documents(entity,
                                                             limit=limit,
                                                             offset_id=offset_id,
                                                             filter_music=filter_music,
                                                             reverse=reverse)

    result = [dataclasses.asdict(dh.document) for dh in documents_handles]

    if json_output:
        print(json.dumps(result, cls=DateTimeEncoder))
    else:
        for d in result:
            print("%s\t%s" % (d['message_id'], d['attributes']['file_name']))


def create_new_files_handler(client: TelegramFsClient, entity, telegram_fs):
    async def new_files_handler(update):

        # logging.debug("update: %s" % update)

        if not isinstance(update, (types.UpdateNewMessage, types.UpdateNewChannelMessage)):
            # logging.debug("Not instance UpdateNewMessage or UpdateNewChannelMessage")
            return

        update_entity_id = None

        if isinstance(update, types.UpdateNewChannelMessage):
            if not update.message.to_id:
                return
            update_entity_id = update.message.to_id.channel_id
            if update_entity_id != entity.id:
                # logging.debug("Not required channel id %d != %d" % (update_entity_id, entity.id))
                return

        elif isinstance(update, types.UpdateNewMessage):
            update_entity_id = update.message.chat_id
            if update_entity_id != entity.id:
                # logging.debug("Not required chat id %d != %d" % (update_entity_id, entity.id))
                return

        msg = update.message
        logging.debug("NewMessage = update_entity_id=%d" %
                      (update_entity_id,))

        if not getattr(msg, 'media', None):
            return

        if not getattr(msg.media, 'document', None):
            return

        document_handle = client.get_document_handle(msg)

        if not document_handle:
            return

        telegram_fs.add_file(msg, document_handle)
        logging.info("New file: %s" % document_handle)

    return new_files_handler


async def mount(client, id, destination: str, offset_id=0, limit=None,
                filter_music=False, debug_fuse=False, reverse=False, updates=False, fsname="tgfs"):
    pyfuse3_asyncio.enable()
    fuse_options = set(pyfuse3.default_options)
    fuse_options.add('fsname=' + fsname)

    if debug_fuse:
        fuse_options.add('debug')

    # in order to use numeric id
    if isinstance(id, int):
        await client.get_dialogs()

    logging.debug("Querying entity %s" % id)

    entity = await client.get_entity(id)

    logging.debug("Got '%s'" % get_display_name(entity))

    logging.info("Querying %s messages starting with message_id %d, music: %s" %
                 (limit if limit else "all", offset_id, filter_music))

    messages, documents_handles = await client.get_documents(entity,
                                                             limit=limit,
                                                             filter_music=filter_music,
                                                             offset_id=offset_id,
                                                             reverse=reverse)

    logging.info("Mounting %d files to %s" % (len(documents_handles), destination))
    # logging.debug("Files: %s" % ([doc['id'] for msg, doc in documents], ))

    telegram_fs = TelegramFsAsync()

    for msg, dh in zip(messages, documents_handles):
        telegram_fs.add_file(msg, dh)

    if updates:
        client.add_event_handler(
            create_new_files_handler(client, entity, telegram_fs))

    pyfuse3.init(telegram_fs, destination, fuse_options)

    await pyfuse3.main(min_tasks=10)


async def download(client: TelegramFsClient, id, destination: str, files: List[int]):
    logging.info("Download files %s from %s to %s" %
                 (files, id, destination))

    logging.debug("Querying entity %s(%s)" % (type(id), id))

    entity = await client.get_entity(id)

    documents = await client.get_documents(entity, ids=files)

    logging.info("Files %s" %
                 ([d['attributes']['file_name'] for m, d in documents],))

    # logging.debug("Files %s" % ([m.id for m, d in documents], ))

    for (msg, doc) in documents:

        if not msg.id in files:
            logging.error("Wrong message id %d" % msg.id)
            continue

        file_name = doc['attributes']['file_name']
        size = doc['size']

        logging.info("Downloading %s, %d bytes" % (file_name, doc['size']))

        with tqdm(total=int(size / 1024), unit='KB') as t:
            await client.download_media(
                msg,
                "%s/%d %s" % (destination, msg.id, file_name),
                progress_callback=lambda recvd, total: t.update(int(131072 / 1024)))
