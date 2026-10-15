"""S06 Driver's licence eligibility (Goossens et al. 2023, GPT-DMN "Driver's license")."""


def decide(age, national_resident, theory, driving, maneuvering, anticipation):
    if age < 18 or not national_resident:
        return "Not eligible"
    if "Fail" in (theory, driving, maneuvering, anticipation):
        return "Not eligible"
    return "Eligible"
