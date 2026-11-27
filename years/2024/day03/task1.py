import re


def solve(input_data: str) -> int | str:
    res = 0
    for left, right in re.findall(r"mul\((\d{1,3}),(\d{1,3})\)", input_data):
        res += int(left) * int(right)
    return res
