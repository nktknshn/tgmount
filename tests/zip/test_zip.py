import struct
import zipfile

from typing import Optional
from zipfile import ZipFile, ZipInfo

# from tgmount.zip.util import build_dirs_tree


def decodeExtra(zinfo: ZipInfo) -> Optional[str]:
    # Try to decode the extra field.
    extra = zinfo.extra
    unpack = struct.unpack

    while len(extra) >= 4:
        tp, ln = unpack("<HH", extra[:4])

        if tp == 0x7075:
            data = extra[4 : ln + 4]
            # Unicode Path Extra Field
            up_version, up_name_crc = unpack("<BL", data[:5])
            up_unicode_name = data[5:].decode("utf-8")

            return up_unicode_name
            # if up_version == 1 and up_name_crc == zinfo.orig_filename_crc:
            #     zinfo.filename = up_unicode_name

        extra = extra[ln + 4 :]


def test_zip():
    zf = zipfile.ZipFile("tests/fixtures/zip2.zip")

    p = zipfile.Path(zf, "/")

    for item in p.iterdir():
        print(item)

    # for f in zf.infolist():
    #     print(f.filename)
    #     print(decodeExtra(f))
