"""S02 NextDate: which action produces the next date (Jorgensen 2013, ch. 7)."""


def is_leap(year):
    return (year % 4 == 0 and year % 100 != 0) or year % 400 == 0


def decide(day, month, year):
    if month == 2:
        if is_leap(year):
            last = 29
        else:
            last = 28
    elif month in (4, 6, 9, 11):
        last = 30
    else:
        last = 31
    if day > last:
        return "Invalid date"
    if day < last:
        return "Next day same month"
    if month == 12:
        return "First day of next year"
    return "First day of next month"
