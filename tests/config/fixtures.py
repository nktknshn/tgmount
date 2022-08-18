import os
import pytest


@pytest.fixture
def config_from_file():
    with open("tests/config/config.yaml", "r+") as f:
        return f.read()
