from collections import defaultdict


def solve(input_data: str) -> int | str:
    list1 = []
    list2: defaultdict[int, int] = defaultdict(int)
    for line in input_data.splitlines():
        n1, n2 = map(int, line.split())
        list1.append(n1)
        list2[n2] += 1
    return sum(value * list2.get(value, 0) for value in list1)
