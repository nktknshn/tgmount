import funcy as funcy

cmap = funcy.curry(map)
compose = funcy.compose
group_by = funcy.group_by
walk_values = funcy.walk_values
fst = lambda a: a[0]
endswith = funcy.partial(funcy.rpartial, str.endswith)
list_map = compose(list, map)
set_map = compose(set, map)
list_filter = compose(list, filter)

""" 
turns
[
    ['a', 'b1', 'a'],
    ['a', 'b1', 'b'],
    ['a', 'b1', 'c'],
    ['a', 'b2', 'a'],
    ['a', 'b2', 'b'],
    ['a', 'b2', 'c'],
]
into 
{
    a: {
        b1: { a, b, c },
        b2: { a, b, c },
    }
}
"""


def build_dirs_tree(dirs_as_lists: list[list[str]]):
    dirs_as_lists = list(filter(len, dirs_as_lists))
    return dict(
        walk_values(
            compose(build_dirs_tree, cmap(lambda r: r[1:])),
            group_by(fst, dirs_as_lists),
        )
    )
