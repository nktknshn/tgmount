import os
from typing import List, Optional
import pytest

from tgmount.vfs.dir import root, dir_content_from_dir, file_content_from_file, vdir
from tgmount.vfs.file import file_content_from_file, text_file, text_content, vfile, text_content
from tgmount.vfs.lookup import get_by_path_str
from tgmount.vfs.types.dir import DirLike, DirContentItem, is_directory
from tgmount.vfs.util import norm_and_parse_path


@pytest.mark.asyncio
async def test_get_by_path_str():

    file1 = vfile('text1.txt', text_content('hello people\n'))
    file2 = vfile('text2.txt', text_content('hello animals\n'))
    file3 = vfile('text3.txt', text_content('hello trees\n'))
    file4 = vfile('text4.txt', text_content('hello planets\n'))
    file5 = vfile('text5.txt', text_content('hello stars\n'))
    file6 = vfile('text6.txt', text_content('hello gravity\n'))

    subfolder1 = vdir('subfolder1', [file4])

    subfolder2 = vdir('subfolder2', [file5])

    folder1 = vdir('folder1', [
        subfolder1,
        subfolder2,
        file6,
    ])

    structure = root(file1, file2, file3, folder1)

    assert await get_by_path_str(structure, '/') is structure
    assert await get_by_path_str(structure, '/text1.txt') is file1

    # trailing slash is ignored
    assert await get_by_path_str(structure, '/text1.txt/') is file1

    #  since the function prenormalizes path this is valid
    assert await get_by_path_str(structure, '/text1.txt/../text1.txt') is file1
    assert await get_by_path_str(structure,
                                 '/text1.txt/../text1.txt/') is file1

    assert await get_by_path_str(structure, 'text1.txt') is file1
    assert await get_by_path_str(structure, 'text666.txt') is None
    assert await get_by_path_str(structure, '/folder1') is folder1
    assert await get_by_path_str(structure, 'folder1') is folder1
    assert await get_by_path_str(structure, 'folder1/subfolder1') is subfolder1
    assert await get_by_path_str(structure,
                                 'folder1/subfolder1/text4.txt') is file4
    assert await get_by_path_str(structure,
                                 'folder1/text1.txt/text4.txt') is None

    # assert await get_by_path_str(
    #     structure, 'folder1/text1.txt/text4.txt/../../') is folder1
