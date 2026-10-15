"""S05 Pet adoption (Goossens et al. 2023, GPT-DMN 'Determine pet')."""


def decide(allergies, time, kids, garden):
    if allergies:
        if time == "none":
            return "No pet"
        return "Fish"
    if time == "none" and not kids:
        return "No pet"
    if kids and time != "a lot":
        return "Fish"
    if garden:
        return "Dog"
    return "Cat"
