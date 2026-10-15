"""S12 Personal-loan screening (authored for this benchmark)."""


def decide(age, credit_score, monthly_income, has_cosigner):
    if age < 21 or credit_score < 600:
        return "Rejected"
    if credit_score >= 750 or monthly_income >= 50000 or has_cosigner:
        return "Approved"
    return "Referred"
