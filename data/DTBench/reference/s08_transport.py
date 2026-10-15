"""S08 Mode of transportation (Goossens et al. 2023, GPT-DMN; boundaries clarified)."""


def decide(distance, weather, hurry):
    if distance < 2:
        if hurry:
            return "bike"
        return "walk"
    if distance < 5:
        if weather == "rainy" or hurry:
            return "car"
        return "bike"
    if distance < 10:
        if weather == "rainy" or hurry or weather == "freezing":
            return "car"
        return "bike"
    if hurry or weather in ("rainy", "freezing"):
        return "car"
    return "bike"
