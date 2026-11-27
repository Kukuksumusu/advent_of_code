def solve(input_data: str) -> int | str:
    list1, list2 = [], []
    for line in input_data.splitlines():
        n1, n2 = map(int, line.split())
        list1.append(n1)
        list2.append(n2)
    list1.sort()
    list2.sort()
    return sum(abs(list1[i] - list2[i]) for i in range(len(list1)))
