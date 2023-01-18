import pytest


@pytest.fixture()
def mnt_dir(tmpdir):
    """str(tmpdir)"""
    return str(tmpdir)
