from typing import Any
import pytest
import yaml
import os
from pprint import pprint
from tgmount.config import *
from tgmount.config import root

from .fixtures import config_from_file


def test_config1(config_from_file: str):
    cfg_dict: dict = yaml.safe_load(config_from_file)

    cfg = Config.from_dict(cfg_dict)

    pprint(cfg)


def make_config_dict(
    client=dict(
        session="tgfs",
        api_id=123,
        api_hash="4df32e662e9599ad4aab5f9e71c2eb7b",
    ),
    message_sources=dict(
        s1=dict(entity="es1"),
        s2=dict(entity="es2"),
        s3=dict(entity="es3"),
        s4=dict(entity="es4"),
    ),
    root=dict(
        groups=dict(
            group1=dict(
                source="s1",
                dirs=dict(docs={"filter": "filt1"}),
            ),
            group2=dict(
                source="s2",
                dirs=dict(docs={"filter": ["filt1", "filt2"]}),
            ),
        ),
        chats=dict(
            chat1=dict(
                source="s3",
                dirs=dict(docs={"filter": ["filt1", "filt3"]}),
            ),
            chat2=dict(
                source="s4",
                dirs=dict(docs={"filter": ["filt4", "filt5"]}),
            ),
        ),
    ),
):
    return dict(
        client=client,
        message_sources=message_sources,
        root=root,
    )


def make_config(**kwargs):
    return yaml.dump(make_config_dict(**kwargs))


def make_config_modify(
    f: Callable[[dict[str, Any]], dict[str, Any]],
    **kwargs,
):
    return yaml.dump(f(make_config_dict(**kwargs)))


# def test_config_parse1():
#     cfg = Config.from_yaml(
#         make_config(
#             message_sources=dict(
#                 s1=dict(entity="es1"),
#             ),
#             root=dict(a={"source": "s1"}, b={"source": "nondefined"}),
#         ),
#     )


def test_config_verify1():
    """should verify if sources used in root are described in message_sources"""

    class ConfigValidator(ConfigValidatorBase):
        pass

    v = ConfigValidator()

    cfg = Config.from_yaml(
        make_config(
            message_sources=dict(
                s1=dict(entity="es1"),
            ),
            root=dict(a={"source": "s1"}, b={"source": "nondefined"}),
        ),
    )

    with pytest.raises(ConfigVerificationError, match="Missing sources"):
        v.verify_config(cfg)


def test_verify_filters1():
    class ConfigValidator(ConfigValidatorBase):
        available_filters: list[str] = ["f1", "f2", "f3"]

    root = dict(
        a={"source": "s1", "dirs": {"a": {"filter": "f1"}}},
        b={
            "source": "s1",
            "filter": ["f1", "f2"],
        },
    )

    ConfigValidator().verify_filters(
        Config.from_yaml(make_config(root=root)),
    )

    with pytest.raises(ConfigVerificationError, match="Missing filters"):
        ConfigValidator().verify_filters(
            Config.from_yaml(
                make_config(
                    root={
                        **root,
                        "c": {"source": "s1", "filter": "missed"},
                    }
                )
            ),
        )

    # verify_filters()
