from enum import Enum
from itertools import pairwise


class Order(Enum):
    ASC = 1
    DESC = -1


def first_invalid_index(order: Order, levels: list[int]) -> int | None:
    """Return index of first invalid step. Returns None if all valid."""
    return next(
        (
            i
            for i, (current, previous) in enumerate(pairwise(levels))
            if not 1 <= order.value * (previous - current) <= 3
        ),
        None,
    )


def is_safe_with_dampener(order: Order, levels: list[int]) -> bool:
    invalid = first_invalid_index(order, levels)
    if invalid is None:
        return True
    return any(first_invalid_index(order, levels[:i] + levels[i + 1 :]) is None for i in range(invalid, invalid + 2))


def solve(input_data: str) -> int | str:
    result = 0
    for report in input_data.splitlines():
        levels = list(map(int, report.split()))

        if not is_safe_with_dampener(Order.ASC, levels) and not is_safe_with_dampener(Order.DESC, levels):
            continue
        result += 1

    return result
