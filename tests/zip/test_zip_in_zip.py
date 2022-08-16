# import pytest
# from tgmount.vfs import (
#     dir_content,
#     root,
#     vfile,
#     file_content_from_io,
# )
# from tgmount.vfs.dir import dir_content_get_tree, file_like_tree_map
# from tgmount.zip import zips_as_dirs

# from ..util import ZipSourceTree, create_zip_from_tree, get_file_content_str_utf8


# @pytest.mark.asyncio
# async def test_zip_in_zip1():
#     """ """

#     sts = {
#         "a1.txt": "a1.txt content",
#         "a2.txt": "a2.txt content",
#         "sf1": {
#             "a3.txt": "a3.txt content",
#             "a4.txt": "a4.txt content",
#         },
#     }

#     st1 = {f"zip1_{k}": v for k, v in sts.items()}
#     st2 = {f"zip2_{k}": v for k, v in sts.items()}

#     z1, d1 = create_zip_from_tree(st1)
#     z2, d2 = create_zip_from_tree(st2)

#     st: ZipSourceTree = {
#         "a1.txt": "a1.txt content",
#         "a2.txt": "a2.txt content",
#         "zip1.zip": d1,
#         "zip2.zip": d2,
#     }

#     z, d = create_zip_from_tree(st)

#     structure = root(
#         zips_as_dirs(
#             dir_content(vfile("archive.zip", file_content_from_io(d))),
#             skip_folder_if_single_subfolder=True,
#         )
#     )

#     tree = await dir_content_get_tree(structure.content)

#     t = await file_like_tree_map(tree, get_file_content_str_utf8)

#     assert t == {
#         "archive.zip": {
#             "a1.txt": "a1.txt content",
#             "a2.txt": "a2.txt content",
#             "zip1.zip": st1,
#             "zip2.zip": st2,
#         }
#     }
