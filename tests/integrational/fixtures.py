from typing import Any
from attr import dataclass
import pytest
from .integrational_test import TgmountIntegrationContext as Context
from ..helpers.fixtures import mnt_dir
from ..helpers.mocked.mocked_storage import MockedSender, StorageEntity
from tgmount.util import none_fallback
from tgmount.tgmount.producers.producer_by_sender import VfsTreeDirBySender


@pytest.fixture
def ctx(mnt_dir, caplog):
    return Context(mnt_dir)


@pytest.fixture
def source1(ctx):
    return ctx.storage.get_entity("source1")


@pytest.fixture
def source2(ctx):
    return ctx.storage.get_entity("source2")


@dataclass
class FixtureFiles:
    picture0: str
    picture1: str
    picture2: str
    picture3: str
    Hummingbird: str

    music0: str
    music1: str
    music2: str
    music_long: str

    zip_debrecen: str
    zip_bandcamp: str

    video0: str
    video1: str


@pytest.fixture
def files():
    return FixtureFiles(
        Hummingbird="tests/fixtures/files/pictures/Hummingbird.jpg",
        picture0="tests/fixtures/files/pictures/debrecen_001.jpg",
        picture1="tests/fixtures/files/pictures/debrecen_002.jpg",
        picture2="tests/fixtures/files/pictures/debrecen_003.jpg",
        picture3="tests/fixtures/files/pictures/debrecen_004.jpg",
        music0="tests/fixtures/files/music/kareem.mp3",
        music1="tests/fixtures/files/music/suffering_hour.mp3",
        music2="tests/fixtures/files/music/dermovyj-raj.mp3",
        music_long="tests/fixtures/files/music/Forlate.mp3",
        zip_debrecen="tests/fixtures/files/zips/2010_debrecen.zip",
        zip_bandcamp="tests/fixtures/files/zips/bandcamp1.zip",
        video0="tests/fixtures/files/videos/000bbadb-b42d-48ac-816f-11c8756487b5.mp4",
        video1="tests/fixtures/files/videos/video_2022-10-13_15-36-27.mp4",
    )


class Fixtures:
    files: FixtureFiles
    mnt_dir: str
    caplog: Any


@pytest.fixture
def fixtures(mnt_dir: str, caplog, files: FixtureFiles):
    f = Fixtures()
    f.files = files
    f.caplog = caplog
    f.mnt_dir = mnt_dir
    return f


class _Context(Context):
    expected_dirs: dict
    senders: dict[str, list]
    source1: StorageEntity
    source2: StorageEntity
    files: FixtureFiles

    @staticmethod
    def from_fixtures(fixtures: Fixtures):
        ctx = _Context(fixtures.mnt_dir, caplog=fixtures.caplog)
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
