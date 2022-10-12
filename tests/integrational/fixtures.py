from attr import dataclass
import pytest
from .integrational_test import (
    TgmountIntegrationContext as Context,
    read_bytes,
    mnt_dir,
)


@pytest.fixture
def ctx(mnt_dir):
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
        picture0="tests/fixtures/files/pictures/Hummingbird.jpg",
        picture1="tests/fixtures/files/pictures/debrecen_001.jpg",
        picture2="tests/fixtures/files/pictures/debrecen_002.jpg",
        picture3="tests/fixtures/files/pictures/debrecen_003.jpg",
        music0="tests/fixtures/files/music/Fr3sh   Kareem Lotfy.mp3",
        music1="tests/fixtures/files/music/For the Putridity of Man   Suffering Hour.mp3",
        music2="tests/fixtures/files/music/gerasim-gruppa-panika-dermovyj-raj-1996-004-12567-80_(mp3CC.biz).mp3",
        music_long="tests/fixtures/files/music/Forlate.mp3",
    )
