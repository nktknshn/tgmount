import getpass
import getpass
import logging
from typing import Dict

from funcy import func_partial
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import (DocumentAttributeAudio,
                               DocumentAttributeFilename,
                               InputDocumentFileLocation,
                               InputMessagesFilterMusic)
from telethon.utils import get_display_name

logger = logging.getLogger('tgclient')

MB = 1048576
KB = 1024
BLOCK_SIZE = 128 * KB


def block(byte_idx: int):
    return byte_idx // BLOCK_SIZE


def block_mb(block_idx: int):
    return (block_idx * BLOCK_SIZE) // MB


def mb(byte: int):
    return byte // MB


def split_range(offset: int, limit: int, block_size=BLOCK_SIZE):
    """
    Restrictions on upload.getFile and upload.getCdnFile parameters
    offset must be divisible by 4096 bytes
    limit must be divisible by 4096 bytes
    10485760 (1MB) must be divisible by limit
    offset / (1024 * 1024) == (offset + limit - 1) / (1024 * 1024)
    (file parts that are being downloaded must always be inside the same megabyte-sized fragment)
    """
    if offset % 4096 != 0:
        offset = (offset // 4096) * 4096

    if limit % 4096 != 0:
        limit = (limit // 4096 + 1) * 4096

    a = offset
    b = offset + limit

    starting_block = block(a)
    ending_block = block(b - 1)

    blocks = list(range(starting_block, ending_block + 1))

    rngs = list(map(lambda b: b * block_size, blocks))
    rngs.append(rngs[-1] + block_size)

    return rngs


def msg_to_inputlocation(msg):
    return InputDocumentFileLocation(id=msg.media.document.id,
                                     access_hash=msg.media.document.access_hash,
                                     file_reference=msg.media.document.file_reference,
                                     thumb_size='')


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
        """
        Returns mapping dialog_display_name -> dialog
        """
        logger.debug("get_dialogs_map(limit=%s, offset_id=%d)" %
                     (limit, offset_id))
        dialogs = await self.get_dialogs(limit=limit, offset_id=offset_id)

        entities = [(get_display_name(d.entity), d.entity) for d in dialogs]

        return dict(entities)

    async def get_file_chunk(self, input_location, offset, limit, *, request_size=BLOCK_SIZE):
        ranges = split_range(offset, limit, request_size)

        result = bytes()

        async for chunk in self.iter_download(input_location,
                                              offset=ranges[0],
                                              request_size=request_size,
                                              limit=len(ranges) - 1):
            result += chunk

        return result[offset - ranges[0]: offset - ranges[0] + limit]

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
