def get_bytes_count(block_size: int | str) -> int:
    if isinstance(block_size, int):
        return block_size

    if block_size.endswith("KB"):
        return int(block_size[:-2]) * 1024

    if block_size.endswith("MB"):
        return int(block_size[:-2]) * 1024 * 1024

    try:
        return int(block_size)
    except ValueError:
        raise ValueError(f"invalid block_size: {block_size}")
