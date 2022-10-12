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
