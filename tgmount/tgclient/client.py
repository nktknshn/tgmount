import logging
from typing import Optional, Union
import typing
import telethon
from telethon import TelegramClient
import asyncio
from .auth import TelegramAuthen
from .search import TelegramSearch

logger = logging.getLogger("tgclient")


class TgmountTelegramClient(TelegramClient, TelegramAuthen, TelegramSearch):
    def __init__(
        self,
        session_user_id,
        api_id,
        api_hash,
        *,
        connection: "typing.Type[telethon.network.Connection]" = telethon.network.ConnectionTcpFull,
        use_ipv6: bool = False,
        proxy: Optional[typing.Union[tuple, dict]] = None,
        local_addr: Optional[typing.Union[str, tuple]] = None,
        timeout: int = 10,
        request_retries: int = 5,
        connection_retries: int = 5,
        retry_delay: int = 1,
        auto_reconnect: bool = True,
        sequential_updates: bool = False,
        flood_sleep_threshold: int = 60,
        raise_last_call_error: bool = False,
        device_model: Optional[str] = None,
        system_version: Optional[str] = None,
        app_version: Optional[str] = None,
        lang_code: str = "en",
        system_lang_code: str = "en",
        loop: Optional[asyncio.AbstractEventLoop] = None,
        base_logger: Optional[typing.Union[str, logging.Logger]] = None,
        receive_updates: bool = True
    ):

        super().__init__(
            session_user_id,
            api_id,
            api_hash,
            connection=connection,
            use_ipv6=use_ipv6,
            local_addr=local_addr,
            timeout=timeout,
            request_retries=request_retries,
            connection_retries=connection_retries,
            retry_delay=retry_delay,
            auto_reconnect=auto_reconnect,
            sequential_updates=sequential_updates,
            flood_sleep_threshold=flood_sleep_threshold,
            raise_last_call_error=raise_last_call_error,
            device_model=device_model,
            system_version=system_version,
            app_version=app_version,
            lang_code=lang_code,
            system_lang_code=system_lang_code,
            loop=loop,
            base_logger=base_logger,
            receive_updates=receive_updates,
            proxy=proxy,
        )  # type: ignore

        # self.api_id = api_id
        # self.api_hash = api_hash
