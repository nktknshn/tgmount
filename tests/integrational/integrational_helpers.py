from typing import Mapping
import yaml

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
