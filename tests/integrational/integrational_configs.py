from typing import Mapping
import yaml
import tgmount.config as config
from tgmount.main.util import read_tgapp_api


DEFAULT_CACHES: Mapping = {
    "memory1": {
        "type": "memory",
        "kwargs": {"capacity": "50MB", "block_size": "128KB"},
    }
}


DEFAULT_ROOT: Mapping = {
    "source1": {
        "source": {"source": "source1", "recursive": True},
        # "all": {"filter": "All"},
        # "wrappers": "ExcludeEmptyDirs",
        # "texts": {"filter": "MessageWithText"},
    },
}

UNPACKED = dict(filter="MessageWithZip", cache="memory1", wrappers="ZipsAsDirs")
BY_SENDER = dict(filter="All", producer="BySender")
WRAPPED_EXCLUDED = {"wrappers": "ExcludeEmptyDirs"}
ONLY_UNIQ_DOCS = {"filter": ["OnlyUniqueDocs"], "recursive": True}
ORGRANIZED: Mapping = yaml.parse(
    """
docs:
  filter:
    - MessageWithOtherDocument
    - Not:
        - ByExtension: .zip
music:
  filter: MessageWithMusic
reactions:
  filter: MessageWithReactions
zips:
  filter: MessageWithZip
personal:
  filter:
    Union: [MessageWithKruzhochek, MessageWithVoice]
video:
  filter: MessageWithVideoFile
images:
  filter:
    Union: [MessageWithDocumentImage, MessageWithCompressedPhoto]
stickers:
  filter:
    Union: [MessageWithAnimated, MessageWithSticker]
messages:
  filter: MessageWithText
  treat_as: MessageWithText
all:
  filter: All
"""
)
ORGRANIZED2 = {
    "filter": {"filter": ["OnlyUniqueDocs"], "recursive": True},
    "docs": {
        "filter": ["MessageWithOtherDocument", {"Not": [{"ByExtension": ".zip"}]}]
    },
    "mixed-audio": {
        "filter": "MessageWithZip",
        "music": {"filter": "MessageWithMusic"},
        "voices": {"filter": "MessageWithVoice"},
    },
    "music": {"filter": "MessageWithMusic"},
    "reactions": {"filter": "MessageWithReactions"},
    "zips": {"filter": "MessageWithZip"},
    "personal": {"filter": {"Union": ["MessageWithKruzhochek", "MessageWithVoice"]}},
    "video": {"filter": "MessageWithVideoFile"},
    "images": {
        "filter": {"Union": ["MessageWithDocumentImage", "MessageWithCompressedPhoto"]}
    },
    "stickers": {"filter": {"Union": ["MessageWithAnimated", "MessageWithSticker"]}},
    "messages": {"filter": "MessageWithText", "treat_as": "MessageWithText"},
    "all": {"filter": "All"},
    "by-forward": {"filter": "MessageForwarded", "producer": "ByForward"},
    "music-by-performer": {"filter": "MessageWithMusic", "producer": "ByPerformer"},
    "forwareded-video": {"filter": {"And": ["MessageForwarded", "MessageWithVideo"]}},
    "unpacked": {
        "filter": "MessageWithZip",
        "cache": "memory1",
        "wrappers": "ZipsAsDirs",
    },
    "wrappers": "ExcludeEmptyDirs",
    "source": {"source": "source1", "recursive": True},
    "by-sender": {
        "filter": "All",
        "producer": {
            "BySender": {
                "dir_structure": {
                    "filter": {"filter": ["OnlyUniqueDocs"], "recursive": True},
                    "docs": {
                        "filter": [
                            "MessageWithOtherDocument",
                            {"Not": [{"ByExtension": ".zip"}]},
                        ]
                    },
                    "mixed-audio": {
                        "filter": "MessageWithZip",
                        "music": {"filter": "MessageWithMusic"},
                        "voices": {"filter": "MessageWithVoice"},
                    },
                    "music": {"filter": "MessageWithMusic"},
                    "reactions": {"filter": "MessageWithReactions"},
                    "zips": {"filter": "MessageWithZip"},
                    "personal": {
                        "filter": {
                            "Union": ["MessageWithKruzhochek", "MessageWithVoice"]
                        }
                    },
                    "video": {"filter": "MessageWithVideoFile"},
                    "images": {
                        "filter": {
                            "Union": [
                                "MessageWithDocumentImage",
                                "MessageWithCompressedPhoto",
                            ]
                        }
                    },
                    "stickers": {
                        "filter": {
                            "Union": ["MessageWithAnimated", "MessageWithSticker"]
                        }
                    },
                    "messages": {
                        "filter": "MessageWithText",
                        "treat_as": "MessageWithText",
                    },
                    "all": {"filter": "All"},
                    "by-forward": {
                        "filter": "MessageForwarded",
                        "producer": "ByForward",
                    },
                    "music-by-performer": {
                        "filter": "MessageWithMusic",
                        "producer": "ByPerformer",
                    },
                    "forwareded-video": {
                        "filter": {"And": ["MessageForwarded", "MessageWithVideo"]}
                    },
                    "unpacked": {
                        "filter": "MessageWithZip",
                        "cache": "memory1",
                        "wrappers": "ZipsAsDirs",
                    },
                    "wrappers": "ExcludeEmptyDirs",
                }
            }
        },
    },
}


def create_config(
    *,
    message_sources={"source1": "source1"},
    caches=DEFAULT_CACHES,
    root: Mapping = DEFAULT_ROOT,
) -> config.Config:
    api_id, api_hash = read_tgapp_api()

    _message_sources = {
        k: config.MessageSource(entity=v) for k, v in message_sources.items()
    }

    _caches = {
        k: config.Cache(type=v["type"], kwargs=v["kwargs"]) for k, v in caches.items()
    }

    return config.Config(
        client=config.Client(api_id=api_id, api_hash=api_hash, session="tgfs"),
        message_sources=config.MessageSources(sources=_message_sources),
        caches=config.Caches(_caches),
        root=config.Root(root),
    )
