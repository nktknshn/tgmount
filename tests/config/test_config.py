from typing import Any
import pytest
import yaml
import os
from pprint import pprint
from tgmount.config import *
from tgmount.config import root, MessageSource

from .fixtures import config_from_file


def test_message_source():
    ms = MessageSource.from_mapping(
        {
            "entity": "abcd",
            "offset_date": "21/10/2023 11:00",
            "filter": "filter",
            "limit": 1000,
            "min_id": 1,
            "max_id": 1,
            "reply_to": 1,
            "wait_time": 0.01,
        }
    )

    assert ms.offset_date == datetime.datetime(2023, 10, 21, 11, 0)
    assert ms.filter == "filter"
    assert ms.reverse is False
    assert ms.wait_time == 0.01
