import re


def solve(input_data: str) -> int | str:
    enabled = True
    res = 0
    for match in re.finditer(r"do\(\)|don't\(\)|mul\((\d{1,3}),(\d{1,3})\)", input_data):
        if match.group(0) == "do()":
            enabled = True
        elif match.group(0) == "don't()":
            enabled = False
        elif enabled:
            res += int(match.group(1)) * int(match.group(2))
    return res
