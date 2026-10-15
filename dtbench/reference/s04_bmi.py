"""S04 BMI level (Goossens et al. 2023, GPT-DMN 'BMI')."""


def decide(gender, weight, length):
    bmi = weight / (length * length)
    if bmi > 30:
        return "Obese"
    if bmi >= 25:
        if gender == "male":
            return "Normal"
        return "Overweight"
    if bmi >= 18.5:
        if gender == "male":
            return "Underweight"
        return "Normal"
    if gender == "male":
        return "Severely underweight"
    return "Underweight"
