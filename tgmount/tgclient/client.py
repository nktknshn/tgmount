import logging

import telethon
from telethon import TelegramClient

from .auth import TelegramAuthen
from .search import TelegramSearch

logger = logging.getLogger("tgclient")


class TgmountTelegramClient(TelegramClient, TelegramAuthen, TelegramSearch):
    def __init__(self, session_user_id, api_id, api_hash, proxy=None):

        super().__init__(session_user_id, api_id, api_hash, proxy=proxy)  # type: ignore

        # self.api_id = api_id
        # self.api_hash = api_hash
