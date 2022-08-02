import os
from tgmount.vfs.util import norm_and_parse_path

# os.path.normpath
# from easy_vfs.util import group_sequences

# def test_group_sequences():
#     assert [
#                *group_sequences([1, 1, 2, 2, 1, 2, 1, 2, 1, 1],
#                                 key=lambda x: x)] \
#            == [
#                [1, 1], [2, 2], [1], [2], [1], [2],
#                [1, 1]]
#     assert [*group_sequences([1, 1, 1, 1, 1], key=lambda x: x)] == [[1, 1, 1, 1, 1]]
#     assert [*group_sequences([], key=lambda x: x)] == []
#     assert [*group_sequences([(1, True), (1, True), (1, False), (1, True), (1, True)],
#                              key=lambda x: x[1])] == [[(1, True), (1, True)], [(1, False)], [(1, True), (1, True)]]


def test_parse_path():
    assert norm_and_parse_path("/") == ["/"]
    assert norm_and_parse_path("/a") == ["/", "a"]
    assert norm_and_parse_path("a") == ["a"]
    assert norm_and_parse_path("a/") == ["a"]
    assert norm_and_parse_path("/a/") == ["/", "a"]
    assert norm_and_parse_path("/a/b") == ["/", "a", "b"]
    assert norm_and_parse_path("a/b") == ["a", "b"]
    assert norm_and_parse_path("/a/b/") == ["/", "a", "b"]
    assert norm_and_parse_path("/a/b/c") == ["/", "a", "b", "c"]


# should normalize
def test_parse_path_norm():
    assert norm_and_parse_path("/.") == [
        "/",
    ]
    assert norm_and_parse_path("/a/..") == [
        "/",
    ]
    assert norm_and_parse_path("a/../a") == ["a"]
    assert norm_and_parse_path("./a/./../a/") == ["a"]
