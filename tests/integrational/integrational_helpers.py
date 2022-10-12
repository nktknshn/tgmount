from typing import Mapping


DEFAULT_ROOT: Mapping = {
    "tmtc": {
        "source": {"source": "tmtc", "recursive": True},
        # "all": {"filter": "All"},
        # "wrappers": "ExcludeEmptyDirs",
        # "texts": {"filter": "MessageWithText"},
    },
}

UNPACKED = dict(filter="MessageWithZip", cache="memory1", wrappers="ZipsAsDirs")
BY_SENDER = dict(filter="All", producer="BySender")
WRAPPED_EXCLUDED = {"wrappers": "ExcludeEmptyDirs"}
