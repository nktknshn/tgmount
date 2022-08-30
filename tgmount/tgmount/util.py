def to_list_of_single_key_dicts(
    items: list[str | dict[str, dict]]
) -> list[str | dict[str, dict]]:
    res = []

    for item in items:
        if isinstance(item, str):
            res.append(item)
        else:
            res.extend(dict([t]) for t in item.items())

    return res
