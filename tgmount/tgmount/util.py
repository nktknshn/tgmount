import json
from datetime import datetime
from typing import List

import socks


def none_or_int(value):
    if value is None:
        return None

    return int(value)


def int_or_string(value):
    try:
        return int(value)
    except ValueError:
        return str(value)


def parse_ids(input_str: str):
    return [int(id) for id in input_str.split(',')]


class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):  # pylint: disable=E0202
        if isinstance(o, datetime):
            return o.isoformat()

        return super().default(o)


def dict_exclude(d: dict, keys: List):
    return {
        k: v for k, v in d.items() if k not in keys
    }


def proxy_arg(value):
    [proxy_host, proxy_port] = value.split(':')
    return (socks.SOCKS5, proxy_host, int(proxy_port))
