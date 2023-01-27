from abc import abstractmethod
from typing import Protocol

from tgmount import config
from tgmount.tgclient.message_types import MessageProto
from tgmount.tgclient.types import TotalListTyped
from tgmount.tgmount.error import TgmountError
from tgmount.util import yes

from .client_types import TgmountTelegramClientGetMessagesProto
from .logger import logger as module_logger

from telethon.tl import types


class TelegramMessagesFetcherProto(Protocol):
    @abstractmethod
    async def fetch(self) -> TotalListTyped[MessageProto]:
        pass


class TelegramMessagesFetcher(TelegramMessagesFetcherProto):
    """Fetches messages for building initial vfs tree"""

    # from_user
    # offset_date
    # offset_id
    # min_id
    # max_id
    # wait_time
    # reply_to
    class_logger = module_logger.getChild(f"TelegramMessagesFetcher")

    FILTERS = {
        "InputMessagesFilterEmpty": types.InputMessagesFilterEmpty,
        "InputMessagesFilterPhotos": types.InputMessagesFilterPhotos,
        "InputMessagesFilterVideo": types.InputMessagesFilterVideo,
        "InputMessagesFilterPhotoVideo": types.InputMessagesFilterPhotoVideo,
        "InputMessagesFilterDocument": types.InputMessagesFilterDocument,
        "InputMessagesFilterUrl": types.InputMessagesFilterUrl,
        "InputMessagesFilterGif": types.InputMessagesFilterGif,
        "InputMessagesFilterVoice": types.InputMessagesFilterVoice,
        "InputMessagesFilterMusic": types.InputMessagesFilterMusic,
        "InputMessagesFilterChatPhotos": types.InputMessagesFilterChatPhotos,
        "InputMessagesFilterPhoneCalls": types.InputMessagesFilterPhoneCalls,
        "InputMessagesFilterRoundVoice": types.InputMessagesFilterRoundVoice,
        "InputMessagesFilterRoundVideo": types.InputMessagesFilterRoundVideo,
        "InputMessagesFilterMyMentions": types.InputMessagesFilterMyMentions,
        "InputMessagesFilterGeo": types.InputMessagesFilterGeo,
        "InputMessagesFilterContacts": types.InputMessagesFilterContacts,
        "InputMessagesFilterPinned": types.InputMessagesFilterPinned,
    }

    def __init__(
        self,
        client: TgmountTelegramClientGetMessagesProto,
        cfg: config.MessageSource,
    ) -> None:
        self.client = client
        self.cfg = cfg
        self.logger = self.class_logger.getChild(str(cfg.entity), suffix_as_tag=True)

    def _get_filter(self, filter_name: str):
        filt = self.FILTERS.get(filter_name)

        if filt is None:
            raise TgmountError(f"Invalid fetcher filter: {self.cfg.filter}")

        return filt

    async def fetch(self):

        self.logger.debug(f"fetching {self.cfg}")

        filt = None

        if yes(self.cfg.filter):
            filt = self._get_filter(self.cfg.filter)

        return await self.client.get_messages(
            self.cfg.entity,
            limit=self.cfg.limit,
            offset_date=self.cfg.offset_date,
            offset_id=self.cfg.offset_id,
            max_id=self.cfg.max_id,
            from_user=self.cfg.from_user,
            reverse=self.cfg.reverse,
            reply_to=self.cfg.reply_to,
            wait_time=self.cfg.wait_time,
            filter=filt,
        )
