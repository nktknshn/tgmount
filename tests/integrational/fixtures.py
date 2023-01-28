import os
from typing import Any
from attr import dataclass
import pytest

from tgmount import vfs, zip as z
from .integrational_test import TgmountIntegrationContext
from ..helpers.fixtures_common import mnt_dir


@pytest.fixture
def ctx(mnt_dir, caplog):
    return TgmountIntegrationContext(mnt_dir)


@pytest.fixture
def source1(ctx):
    return ctx.storage.get_entity("source1")


@pytest.fixture
def source2(ctx):
    return ctx.storage.get_entity("source2")


class FixtureFile:
    def __init__(self, path: str) -> None:
        self.path = path

    @property
    def file_content(self):
        return vfs.file_content_from_file(self.path)

    async def zip_file(self):
        return await z.zip_dir_factory.zipfile_factory(self.file_content)

    @property
    def basename(self):
        return os.path.basename(self.path)

    @property
    def extension(self):
        return os.path.splitext(self.path)[1]

    @property
    def name(self):
        return os.path.splitext(self.path)[0]


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

    zip_debrecen: FixtureFile
    zip_bandcamp: FixtureFile
    zip_bad: FixtureFile
    zip_linux2: FixtureFile
    zip_atrium: FixtureFile

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
        zip_debrecen=FixtureFile("tests/fixtures/files/zips/2010_debrecen.zip"),
        zip_bandcamp=FixtureFile("tests/fixtures/files/zips/bandcamp1.zip"),
        zip_bad=FixtureFile("tests/fixtures/bad_zip.zip"),
        zip_atrium=FixtureFile("tests/fixtures/Atrium Carceri.zip"),
        zip_linux2=FixtureFile("tests/fixtures/linux_zip2.zip"),
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
