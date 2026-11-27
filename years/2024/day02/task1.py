from enum import Enum
from itertools import pairwise


class Order(Enum):
    ASC = 1
    DESC = -1


def solve(input_data: str) -> int | str:
    result = 0
    for report in input_data.splitlines():
        levels = list(map(int, report.split()))
        order = Order.DESC if levels[0] > levels[1] else Order.ASC
        if all(1 <= order.value * (previous - current) <= 3 for current, previous in pairwise(levels)):
            result += 1
    return result
