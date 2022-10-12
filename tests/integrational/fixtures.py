from attr import dataclass
import pytest
from .integrational_test import (
    TgmountIntegrationContext as Context,
    read_bytes,
    mnt_dir,
)


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
    )
