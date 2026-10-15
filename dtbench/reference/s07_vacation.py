"""S07 Vacation days (Goossens et al. 2023 'Holidays'; DMCommunity challenge Jan 2016, J. Vanthienen)."""


def decide(age, years_of_service):
    days = 22
    extra_five = age < 18 or age >= 60 or years_of_service >= 30
    if extra_five:
        days = days + 5
    if years_of_service >= 30 or age >= 60:
        days = days + 3
    if not extra_five and (15 <= years_of_service < 30 or age >= 45):
        days = days + 2
    return days
