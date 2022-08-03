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
