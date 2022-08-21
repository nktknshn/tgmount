from collections.abc import Mapping
from .types import *
from .root import *
from .helpers import *
from tgmount.util import col
from tgmount.tgclient.guards import *
import abc

""" 
[
        "MessageWithCompressedPhoto",
        "MessageWithVideo",
        "MessageWithDocument",
        "MessageWithDocumentImage",
        "MessageWithVoice",
        "MessageWithKruzhochek",
        "MessageWithZip",
        "MessageWithMusic",
        "MessageWithAnimated",
        "MessageWithOtherDocument",
        "MessageWithSticker",
    ]
"""


class ConfigValidatorBase(abc.ABC):

    available_filters: list[str] = []

    def get_available_filters_str(self) -> set[str]:
        return set(self.available_filters)

    def verify_message_sources(self, cfg: Config):
        assert_that(
            len(cfg.message_sources.sources) > 0,
            ConfigVerificationError(f"message_sources must contain at least 1 source"),
        )

        # root_sources = set(map(lambda v: v.source, cfg.root.get_contents_list()))

        # messages_sources = set(cfg.message_sources.sources.keys())

        # missing_sources = root_sources.difference(messages_sources)

        # assert_that(
        #     len(missing_sources) == 0,
        #     ConfigVerificationError(
        #         f"Missing sources in message_sources: {missing_sources}"
        #     ),
        # )

    def verify_filters(self, cfg: Config):
        pass
        # used_filters = cfg.root.get_filters_set()
        # missing_filters = used_filters.difference(self.available_filters)

        # assert_that(
        #     len(missing_filters) == 0,
        #     ConfigVerificationError(f"Missing filters in available: {missing_filters}"),
        # )

    def verify_config(self, cfg: Config):
        self.verify_message_sources(cfg)
        self.verify_filters(cfg)


class ConfigVerificationError(ConfigError):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


# def get_root_filters(root: Root):
#     return fold_tree(
#         lambda v, res: [*res, v.source],
#         root.content,
#         [],
#     )
