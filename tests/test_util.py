import os
from tgmount.vfs.util import norm_and_parse_path
from tgmount import vfs


def test_vfs_split_path():
    print(vfs.split_path("/"))
    # assert vfs.split_path("/") == "/", ""


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

    assert norm_and_parse_path("/a/b/c", True) == ["a", "b", "c"]
    assert norm_and_parse_path("a/b/c", True) == ["a", "b", "c"]
    assert norm_and_parse_path("/", True) == []


# should normalize
def test_parse_path_norm():
    assert norm_and_parse_path("/.") == ["/"]
    assert norm_and_parse_path("/a/..") == ["/"]
    assert norm_and_parse_path("a/../a") == ["a"]
    assert norm_and_parse_path("./a/./../a/") == ["a"]
