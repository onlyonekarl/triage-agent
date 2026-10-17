# A tiny app with one planted bug.
# average() crashes when the list is empty.

def average(numbers):
    return sum(numbers) / len(numbers)


if __name__ == "__main__":
    print(average([1, 2, 3]))  # prints 2.0
    print(average([]))         # crashes with ZeroDivisionError