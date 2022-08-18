import yaml
import os
from pprint import pprint
from tgmount.config import *

from .fixtures import config_from_file


def test_config1(config_from_file: str):
    cfg_dict: dict = yaml.safe_load(config_from_file)

    cfg = Config.from_dict(cfg_dict)

    pprint(cfg)
