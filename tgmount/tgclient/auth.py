import getpass
import logging

from telethon import client
from telethon.errors import SessionPasswordNeededError

logger = logging.getLogger("tgclient-auth")


class TelegramAuthen:
    async def auth(self: client.TelegramClient):  # type: ignore
        logger.debug("Connecting to Telegram servers...")

        try:
            await self.connect()
        except ConnectionError:
            logger.debug("Initial connection failed. Retrying...")
            if not await self.connect():
                logger.debug("Could not connect to Telegram servers.")
                return

        logger.debug("Connected")

        if await self.is_user_authorized():
            return

        user_phone = input("Enter your phone number: ")

        logger.debug("First run. Sending code request...")

        await self.sign_in(user_phone)

        self_user = None

        while self_user is None:
            code = input("Enter the code you just received: ")
            try:
                self_user = await self.sign_in(code=code)
            except SessionPasswordNeededError:
                pw = getpass.getpass(
                    "Two step verification is enabled. " "Please enter your password: "
                )

                self_user = await self.sign_in(password=pw)
