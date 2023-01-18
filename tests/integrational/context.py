from typing import Any
from attr import dataclass
import pytest
from .integrational_test import TgmountIntegrationContext as Context
from ..helpers.fixtures_common import mnt_dir
from ..helpers.mocked.mocked_storage import MockedSender, StorageEntity
from tgmount.util import none_fallback
from tgmount.tgmount.producers.producer_by_sender import VfsTreeDirBySender
from .fixtures import FixtureFiles, Fixtures


class Context(Context):
    expected_dirs: dict
    senders: dict[str, list]
    source1: StorageEntity
    source2: StorageEntity
    files: FixtureFiles

    @staticmethod
    def from_fixtures(fixtures: Fixtures):
        ctx = Context(fixtures.mnt_dir, caplog=fixtures.caplog)
        ctx.files = fixtures.files
        ctx.init()
        return ctx

    def init(self):
        self.source1 = self.storage.get_entity("source1")
        self.source2 = self.storage.get_entity("source2")

    def create_senders(self, count: int):
        self.expected_dirs = {}
        self.senders = {f"sender_{idx}": [] for idx in range(0, count)}

        for sender_name, messages in self.senders.items():
            sender = MockedSender(sender_name, None)
            self.expected_dirs[sender_name] = VfsTreeDirBySender.sanitize(
                f"{sender.id}_{sender_name}"
            )

    async def send_text_messages(self, count: int, source=None):
        """For every created sender send `count` text messages. By default source1 used as source"""
        source = none_fallback(source, self.source1)

        for sender_name, messages in self.senders.items():
            sender = MockedSender(sender_name, None)
            for msg_idx in range(0, count):
                msg = await source.message(
                    text=f"Message number {msg_idx} from {sender_name}", sender=sender
                )
                messages.append(msg)

    async def send_docs(self, count: int, source=None):
        files = self.files
        source = none_fallback(source, self.source1)
        for sender_name, messages in self.senders.items():
            sender = MockedSender(sender_name, None)
            for msg_idx in range(0, count):
                msg = await source.document(
                    text=f"Message with Hummingbird number {msg_idx} from {sender_name}",
                    sender=sender,
                    file=files.Hummingbird,
                )
                messages.append(msg)

                msg = await source.document(
                    # text=f"Message with music number {msg_idx} from {sender_name}",
                    sender=sender,
                    file=files.music0,
                )
                messages.append(msg)

                msg = await source.document(
                    text=f"Message with zip number {msg_idx} from {sender_name}",
                    sender=sender,
                    file=files.zip_debrecen,
                )
                messages.append(msg)
