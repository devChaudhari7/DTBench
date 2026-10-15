"""S09 Scholarship eligibility (Goossens et al. 2023, GPT-DMN 'scholarship')."""


def decide(grades, annual_income, received_other_scholarship):
    if grades in ("excellent", "good") and annual_income < 50000 and not received_other_scholarship:
        return "Eligible"
    return "Not eligible"
