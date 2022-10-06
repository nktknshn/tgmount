from tgmount.tgclient.guards import *
from .validatorbase import *

filters = [
    MessageWithCompressedPhoto,
    MessageWithVideo,
    MessageWithDocument,
    MessageWithDocumentImage,
    MessageWithVoice,
    MessageWithKruzhochek,
    MessageWithZip,
    MessageWithMusic,
    MessageWithAnimated,
    MessageWithOtherDocument,
    MessageWithSticker,
]


class ConfigValidator(ConfigValidatorBase):
    available_filters: list[str] = [filt.__name__ for filt in filters]
