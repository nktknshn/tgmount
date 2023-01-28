#!/usr/bin/env python

from distutils.core import setup

with open("README.md", "r") as fh:  # description to be used in pypi project page
    long_description = fh.read()

install_requires = ["telethon", "typing_extensions", "greenback", "aiofiles", "pyyaml"]

setup(
    name="tgmount",
    version="1.0",
    description="Mount telegram messages as files",
    author="Nikita Kanashin",
    author_email="nikita@kanash.in",
    url="https://github.com/nktknshn/tgmount-ng",
    packages=["tgmount"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=install_requires,
    scripts=["cli.py"],
)
