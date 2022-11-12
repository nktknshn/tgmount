from tgmount.tgclient import TgmountTelegramClient


class ClientEnv:
    """Authorizes client on enter and disconnects on exit"""

    TelegramClient = TgmountTelegramClient

    def get_client(self, session: str, api_id: int, api_hash: str):
        return self.TelegramClient(
            session,
            api_id,
            api_hash,
        )

    def __init__(self, session, api_id, api_hash):
        self.client = self.get_client(session, api_id, api_hash)

    async def __aenter__(self):
        await self.client.auth()
        return self.client

    async def __aexit__(self, type, value, traceback):
        await self._cleanup()

    async def _cleanup(self):
        if cor := self.client.disconnect():
            await cor
