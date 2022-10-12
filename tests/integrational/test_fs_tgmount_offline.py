import os
from typing import Mapping

import pytest

from ..helpers.mocked.mocked_message import MockedMessage, MockedSender
from .helpers import *
from .integrational_helpers import BY_SENDER, UNPACKED
from .integrational_test import TgmountIntegrationTest, mnt_dir


class TgmountTestZip(TgmountIntegrationTest):
    def create_root(self) -> Mapping:
        return {
            **DEFAULT_ROOT,
            "tmtc": {
                **(DEFAULT_ROOT["tmtc"]),
                "unpacked": UNPACKED,
                "music": dict(filter="MessageWithMusic"),
            },
        }

    async def prepare_storage(self, storage):
        tmtc = storage.get_entity(TESTING_CHANNEL)
        await tmtc.message(message_text="aaaa")
        await tmtc.document_file_message(file="tests/fixtures/2010_debrecen.zip")
        await tmtc.audio_file_message(
            file="tests/fixtures/files/Tvrdý _ Havelka - Žiletky.mp3",
            duration=666,
            performer="behemoth",
            title="Satan",
            file_name="behemoth_satan.mp3",
        )

    async def test(self, storage, client):
        subfiles = await self.listdir("tmtc/all/")
        assert len(subfiles) == 3
        msg1 = await client.send_message(TESTING_CHANNEL, message="lsksksks")
        subfiles = await self.listdir("tmtc/all/")
        assert len(subfiles) == 4
        await client.delete_messages(TESTING_CHANNEL, msg_ids=[msg1.id])
        subfiles = await self.listdir("tmtc/all/")
        assert len(subfiles) == 3
        zips = await self.listdir("tmtc/unpacked/2_2010_debrecen.zip")
        assert "2010_Debrecen" in zips
        music = await self.listdir("tmtc/music")
        assert len(music) == 1


class TgmountTestGrouping(TgmountIntegrationTest):
    def create_root(self) -> Mapping:
        return {
            **DEFAULT_ROOT,
            "tmtc": {**DEFAULT_ROOT["tmtc"], "by-sender": BY_SENDER},
        }

    async def prepare_storage(self, storage):
        tmtc = storage.get_entity(TESTING_CHANNEL)

        self.senders = [f"sender_{idx}" for idx in range(0, 10)]
        self.senders_messages: list[list[MockedMessage]] = [[] for _ in self.senders]

        for sender_id, (sender, messages) in enumerate(
            zip(self.senders, self.senders_messages)
        ):
            for idx in range(0, 10):
                messages.append(
                    await tmtc.message(
                        message_text=f"Message from {sender} number {idx}",
                        sender=MockedSender(sender, sender_id),
                    )
                )

    async def test(self, storage, client):
        subfiles = await self.listdir("tmtc/by-sender/")
        assert len(subfiles) == 10
        await client.delete_messages(
            TESTING_CHANNEL, msg_ids=[self.senders_messages[0][0].id]
        )
        subfiles = await self.listdir(
            f"tmtc/by-sender/{self.senders_messages[0][0].sender.id}_{self.senders[0]}",
        )
        assert len(subfiles) == 9
        await client.delete_messages(
            TESTING_CHANNEL, msg_ids=[m.id for m in self.senders_messages[1]]
        )
        subfiles = await self.listdir("tmtc/by-sender/")
        assert len(subfiles) == 9


@pytest.mark.asyncio
async def test_TgmountTestZip(mnt_dir, caplog):
    await TgmountTestZip.run_test(mnt_dir, caplog)


@pytest.mark.asyncio
async def test_itergrational2(mnt_dir, caplog):
    await MyTest3.test_class(mnt_dir, caplog)
