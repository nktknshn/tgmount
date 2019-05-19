import os
import sys
import asyncio
import logging
from funcy import walk, func_partial, with_next

from telethon import TelegramClient
from telethon.network.connection import tcpabridged
from telethon.tl.custom import dialog

from telethon.crypto import CdnDecrypter
from telethon.errors import SessionPasswordNeededError, FileMigrateError
from telethon.tl.functions.upload import GetFileRequest
from telethon.tl.types import (DocumentAttributeAudio,
                               DocumentAttributeFilename, InputDocumentFileLocation, InputPeerEmpty)
from telethon.tl.types.upload import FileCdnRedirect
from telethon.utils import get_display_name
from telethon.tl.types import InputMessagesFilterMusic
from telethon import utils
from telethon import errors
from telethon import functions
from typing import Dict, Tuple, Sequence, List
import getpass


logger = logging.getLogger('tgclient')

MB = 1048576
KB = 1024
BLOCK_SIZE = 32 * KB


def block(byte_idx: int):
    return byte_idx//BLOCK_SIZE


def block_mb(block_idx: int):
    return (block_idx*BLOCK_SIZE)//MB


def mb(byte: int):
    return byte//MB


def split_range(offset: int, limit: int):

    if offset % 4096 != 0:
        offset = (offset // 4096) * 4096

    if limit % 4096 != 0:
        limit = (limit // 4096 + 1) * 4096

    a = offset
    b = offset + limit

    starting_block = block(a)
    ending_block = block(b - 1)

    blocks = list(range(starting_block, ending_block + 1))

    rngs = list(map(lambda b: b * BLOCK_SIZE, blocks))
    rngs.append(rngs[-1] + BLOCK_SIZE)

    return rngs


def msg_to_inputlocation(msg):
    return InputDocumentFileLocation(id=msg.media.document.id,
                                     access_hash=msg.media.document.access_hash,
                                     file_reference=msg.media.document.file_reference)

 
class TelegramFsClient(TelegramClient):
    def __init__(self, session_user_id, api_id, api_hash, proxy):

        super().__init__(
            session_user_id,
            api_id,
            api_hash,
            proxy=proxy
        )

        self.api_id = api_id
        self.api_hash = api_hash

    async def auth(self):
        logger.debug('Connecting to Telegram servers...')

        try:
            await self.connect()
        except ConnectionError:
            logger.debug('Initial connection failed. Retrying...')
            if not await self.connect():
                logger.debug('Could not connect to Telegram servers.')
                return

        logger.debug('Connected')

        if not await self.is_user_authorized():

            user_phone = input('Enter your phone number: ')

            logger.debug('First run. Sending code request...')

            await self.sign_in(user_phone)

            self_user = None
            while self_user is None:
                code = input('Enter the code you just received: ')
                try:
                    self_user = await self.sign_in(code=code)
                except SessionPasswordNeededError:
                    pw = getpass.getpass('Two step verification is enabled. '
                                         'Please enter your password: ')

                    self_user = await self.sign_in(password=pw)

    async def get_dialogs_dict(self, limit=150, offset_id=0) -> Dict:

        logger.debug("get_dialogs_map(limit=%s, offset_id=%d)" %
                     (limit, offset_id))
        dialogs = await self.get_dialogs(limit=limit, offset_id=offset_id)

        entities = [(get_display_name(d.entity), d.entity) for d in dialogs]

        return dict(entities)

    async def get_file_chunk(self, input_location, offset, limit):
        """
        This reimplementation of telethon's `download_file` method adds offset and limit parametres 
        in order to download arbitrary chunks of a file
        """
        logger.debug("get_file_chunk(%s, %s,%s)" %
                     (input_location.id, offset, limit))

        ranges = split_range(offset, limit)

        received_bytes = bytes()

        assert not offset % 4096

        dc_id, input_location = utils.get_input_location(input_location)
        exported = dc_id and self.session.dc_id != dc_id

        if exported:
            try:
                sender = await self._borrow_exported_sender(dc_id)
            except errors.DcIdInvalidError:
                # Can't export a sender for the ID we are currently in
                config = await self(functions.help.GetConfigRequest())
                for option in config.dc_options:
                    if option.ip_address == self.session.server_address:
                        self.session.set_dc(
                            option.id, option.ip_address, option.port)
                        self.session.save()
                        break

                # TODO Figure out why the session may have the wrong DC ID
                sender = self._sender
                exported = False
        else:
            # The used sender will also change if ``FileMigrateError`` occurs
            sender = self._sender

        # Restrictions on upload.getFile and upload.getCdnFile parameters
        # offset must be divisible by 4096 bytes
        # limit must be divisible by 4096 bytes
        # 10485760 (1MB) must be divisible by limit
        # offset / (1024 * 1024) == (offset + limit - 1) / (1024 * 1024)
        # (file parts that are being downloaded must always be inside the same megabyte-sized fragment)

        try:
            for a, b in with_next(ranges):
                if not b:
                    break

                _offset = a
                _limit = b - a

                logger.debug("Quering range offset=%s limit=%s" %
                             (_offset, _limit))

                try:
                    result = await sender.send(functions.upload.GetFileRequest(
                        input_location, _offset, _limit
                    ))

                    if isinstance(result, FileCdnRedirect):
                        logger.debug("FileCdnRedirect was received")
                        raise NotImplementedError

                except FileMigrateError as e:
                    logger.debug("Caught FileMigrateError")

                    sender = await self._borrow_exported_sender(e.new_dc)
                    exported = True
                    continue

                if not result.bytes:
                    return getattr(result, 'type', '')

                received_bytes += result.bytes

        except Exception as e:
            logger.error("Zero chunk received %s" % e)
        finally:
            logger.debug("Finalization %s" % len(received_bytes))

            if exported:
                await self._return_exported_sender(sender)
            elif sender != self._sender:
                await sender.disconnect()

            ret_data = received_bytes[offset -
                                      ranges[0]: offset - ranges[0] + limit]

            if len(ret_data) == 0:
                logger.error("Empty result")

            logger.debug("Returning %s bytes" % len(ret_data))

            return ret_data

    def document_from_message(self, msg):
        """
        transforms a message containing a document to a dictionary
        """

        if not getattr(msg, 'media', None):
            return None

        if not getattr(msg.media, 'document', None):
            return None

        document = msg.media.document
        document_data = dict.fromkeys([
            'id',
            'message_id',
            'message_date',
            'document_date',
            'mime_type',
            'size',
            'attributes',
            'download_func'])

        document_atrributes = dict.fromkeys([
            'file_name',
            'title',
            'performer',
            'duration'])

        document_data['attributes'] = document_atrributes
        document_data['download_func'] = func_partial(
            self.get_file_chunk, msg_to_inputlocation(msg))

        document_data.update(id=document.id,
                             message_date=msg.date,
                             document_date=document.date,
                             mime_type=document.mime_type,
                             size=document.size, message_id=msg.id)

        for attr in msg.media.document.attributes:
            if isinstance(attr, DocumentAttributeAudio):
                document_atrributes['title'] = getattr(attr, 'title', None)
                document_atrributes['performer'] = getattr(
                    attr, 'performer', None)
                document_atrributes['duration'] = int(
                    getattr(attr, 'duration', 0))

            elif isinstance(attr, DocumentAttributeFilename):
                document_atrributes['file_name'] = attr.file_name

        return document_data

    async def _get_documents(self, entity, limit=None, offset_id=0, reverse=False, filter_music=False, ids=None):
        """
        Returns two lists: list of processed messages and list of tuples (message, document)
        """
        documents = []

        logger.debug("_get_documents(entity=%s, limit=%s, offset_id=%s, reverse=%s, filter_music=%s, ids=%s)"
                     % (entity.id, limit, offset_id, reverse, filter_music, ids))

        messages = await self.get_messages(entity, limit=limit, offset_id=offset_id, reverse=reverse,
                                           filter=filter_music and InputMessagesFilterMusic, ids=ids)

        logger.debug("Received %d messages" % len(messages))

        for msg in messages:
            document = self.document_from_message(msg)
            if document:
                documents.append((msg, document))

        return [messages, documents]

    async def get_documents(self, entity, limit=None, offset_id=0, reverse=False, filter_music=False, ids=None):
        """
        Returns list of tuples (message, document)
        """
        documents = []

        logger.debug("get_documents(entity=%s, limit=%s, offset_id=%s, reverse=%s, filter_music=%s, ids=%s)"
                     % (entity.id, limit, offset_id, reverse, filter_music, ids))

        [messages, documents] = await self._get_documents(entity,
                                                          limit=limit,
                                                          offset_id=offset_id,
                                                          reverse=reverse,
                                                          filter_music=filter_music, 
                                                          ids=ids)

        logger.debug("Received %d documents" % len(documents))

        while not ids and limit and limit > len(documents):
            logger.debug("Loading more documents")
            [messages, more] = await self._get_documents(entity,
                                                         offset_id=messages[-1].id,
                                                         limit=100,
                                                         reverse=reverse,
                                                         filter_music=filter_music)
            logger.debug("Received %d documents" % len(more))

            if len(messages) == 0:
                break

            documents.extend(more)

        return documents[:limit]
