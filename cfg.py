import argparse
import os
import typing
from dataclasses import dataclass, fields
from typing import Optional, Union
from pprint import pprint

import yaml

from tgmount.config import *
from tgmount.util import col


def get_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument("config", type=str, default="tests/config/config.yaml")
    parser.add_argument("--debug", type=bool, default=False)

    return parser


def main():
    # parser = get_parser()

    # args = parser.parse_args()

    args = dict(config="tests/config/config.yaml")

    with open(args["config"], "r+") as f:
        cfg_dict: dict = yaml.safe_load(f)
        cfg = Config.from_dict(cfg_dict)

        pprint(cfg)


if __name__ == "__main__":
    main()
