"""DTBench: twelve business-rule specifications with ground-truth decision tables.

Each specification has the natural-language rules given to the LLM, a data
dictionary (inputs, output, optional constraint), a ground-truth limited-entry
decision table derived manually (Jorgensen's procedure: one rule per distinct
case of the specification, don't-care entries only where the specification makes
a condition irrelevant) and an independent reference implementation.
"""
import itertools

from .model import Spec, Var


def R(rid, when, output):
    return {"id": rid, "when": when, "output": output}


def C(cid, expr):
    return {"id": cid, "expr": expr}


T, F = True, False

GPT_DMN = ("A. Goossens, S. Vandevelde, J. Vanthienen and J. Vennekens, \"GPT-3 for Decision Logic "
           "Modeling\", RuleML+RR 2023 Companion, CEUR-WS Vol. 3485")
GPT_DMN_URL = "https://gitlab.com/EAVISE/sva/GPT-DMN"
JORGENSEN = "P. C. Jorgensen, Software Testing: A Craftsman's Approach, 4th ed., CRC Press, 2013, ch. 7"


# --------------------------------------------------------------------------------------
# extra evaluation probes (dense grids where the domain is small)
# --------------------------------------------------------------------------------------
def _triangle_extra(spec, rng):
    pts = [dict(a=a, b=b, c=c) for a, b, c in itertools.product(range(1, 11), repeat=3)]
    for _ in range(3000):
        a, b = rng.randint(1, 120), rng.randint(1, 120)
        for c in (a + b - 1, a + b, a + b + 1):
            if 1 <= c <= 200:
                pts.append(dict(a=a, b=b, c=c))
                pts.append(dict(a=c, b=a, c=b))
                pts.append(dict(a=b, b=c, c=a))
    for x in (1, 2, 100, 199, 200):
        pts += [dict(a=x, b=x, c=x), dict(a=x, b=x, c=1), dict(a=1, b=x, c=x)]
    return pts


def _nextdate_extra(spec, rng):
    years = (1900, 1901, 1904, 1996, 1999, 2000, 2001, 2023, 2024, 2096, 2100)
    return [dict(day=d, month=m, year=y) for y in years for m in range(1, 13) for d in range(1, 32)]


def _bmi_extra(spec, rng):
    pts = []
    for length in (1.5, 2.0):
        for bmi in (18.5, 25.0, 30.0):
            for delta in (-0.1, -0.01, 0.0, 0.01, 0.1):
                w = round((bmi + delta) * length * length, 6)
                for g in ("male", "female"):
                    pts.append(dict(gender=g, weight=w, length=length))
    return pts


def _licence_extra(spec, rng):
    levels = ("Excellent", "Good", "Fail")
    pts = []
    for age in (14, 17, 18, 19, 40, 90):
        for res in (False, True):
            for sk in itertools.product(levels, repeat=4):
                pts.append(dict(age=age, national_resident=res, theory=sk[0], driving=sk[1],
                                maneuvering=sk[2], anticipation=sk[3]))
    return pts


def _vacation_extra(spec, rng):
    return [dict(age=a, years_of_service=s) for a in range(16, 71) for s in range(0, 55)]


def _login_extra(spec, rng):
    return [dict(account_locked=l, password_correct=p, failed_attempts=n, trusted_device=t, otp_verified=o)
            for l, p, n, t, o in itertools.product((F, T), (F, T), range(10), (F, T), (F, T))]


# --------------------------------------------------------------------------------------
SPECS = [
    Spec(
        id="S01", name="Triangle classification", category="Textbook",
        source=JORGENSEN + "; G. J. Myers et al., The Art of Software Testing, 3rd ed., Wiley, 2011",
        source_url="",
        rules_text=(
            "The program reads three integer side lengths a, b and c and classifies the triangle they form. "
            "If any one side is greater than or equal to the sum of the other two sides, the three sides cannot "
            "form a triangle and the output is \"Not a triangle\". Otherwise, the output is \"Equilateral\" if all "
            "three sides are equal, \"Isosceles\" if exactly two sides are equal, and \"Scalene\" if no two sides "
            "are equal."),
        inputs=[Var("a", "int", 1, 200, desc="side length"), Var("b", "int", 1, 200, desc="side length"),
                Var("c", "int", 1, 200, desc="side length")],
        output_name="triangle_type", output_type="enum",
        output_values=("Not a triangle", "Scalene", "Isosceles", "Equilateral"),
        gt_table={
            "conditions": [C("C1", "a < b + c"), C("C2", "b < a + c"), C("C3", "c < a + b"),
                           C("C4", "a == b"), C("C5", "a == c"), C("C6", "b == c")],
            "rules": [
                R("R1", {"C1": F}, "Not a triangle"),
                R("R2", {"C1": T, "C2": F}, "Not a triangle"),
                R("R3", {"C1": T, "C2": T, "C3": F}, "Not a triangle"),
                R("R4", {"C1": T, "C2": T, "C3": T, "C4": T, "C5": T, "C6": T}, "Equilateral"),
                R("R5", {"C1": T, "C2": T, "C3": T, "C4": T, "C5": F, "C6": F}, "Isosceles"),
                R("R6", {"C1": T, "C2": T, "C3": T, "C4": F, "C5": T, "C6": F}, "Isosceles"),
                R("R7", {"C1": T, "C2": T, "C3": T, "C4": F, "C5": F, "C6": T}, "Isosceles"),
                R("R8", {"C1": T, "C2": T, "C3": T, "C4": F, "C5": F, "C6": F}, "Scalene"),
            ],
            "infeasible_rules": [
                {"when": {"C1": T, "C2": T, "C3": T, "C4": T, "C5": T, "C6": F}, "note": "a=b and a=c imply b=c"},
                {"when": {"C1": T, "C2": T, "C3": T, "C4": T, "C5": F, "C6": T}, "note": "a=b and b=c imply a=c"},
                {"when": {"C1": T, "C2": T, "C3": T, "C4": F, "C5": T, "C6": T}, "note": "a=c and b=c imply a=b"},
            ],
        },
        reference="s01_triangle", tags=("relational conditions", "impossible combinations"),
        extra_probes=_triangle_extra,
    ),
    Spec(
        id="S02", name="NextDate", category="Textbook", source=JORGENSEN, source_url="",
        rules_text=(
            "Given a date as day, month and year, the program decides how the date of the next day is obtained. "
            "Months 1, 3, 5, 7, 8, 10 and 12 have 31 days; months 4, 6, 9 and 11 have 30 days; month 2 (February) "
            "has 29 days in a leap year and 28 days otherwise. A year is a leap year if it is divisible by 4 but not "
            "by 100, or if it is divisible by 400. If the day does not exist in that month and year (for example "
            "day 31 of month 4, or day 29 of February in a non-leap year), the output is \"Invalid date\". If the "
            "day is before the last day of its month, the output is \"Next day same month\". If the day is the last "
            "day of month 12, the output is \"First day of next year\". If the day is the last day of any other "
            "month, the output is \"First day of next month\"."),
        inputs=[Var("day", "int", 1, 31), Var("month", "int", 1, 12), Var("year", "int", 1900, 2100)],
        output_name="next_date_action", output_type="enum",
        output_values=("Invalid date", "Next day same month", "First day of next month", "First day of next year"),
        gt_table={
            "conditions": [C("C1", "month in (4, 6, 9, 11)"), C("C2", "month in (1, 3, 5, 7, 8, 10)"),
                           C("C3", "month == 12"), C("C4", "day <= 27"), C("C5", "day == 28"),
                           C("C6", "day == 29"), C("C7", "day == 30"),
                           C("C8", "(year % 4 == 0 and year % 100 != 0) or year % 400 == 0")],
            "rules": [
                R("R1", {"C1": T, "C4": T}, "Next day same month"),
                R("R2", {"C1": T, "C5": T}, "Next day same month"),
                R("R3", {"C1": T, "C6": T}, "Next day same month"),
                R("R4", {"C1": T, "C7": T}, "First day of next month"),
                R("R5", {"C1": T, "C4": F, "C5": F, "C6": F, "C7": F}, "Invalid date"),
                R("R6", {"C2": T, "C4": T}, "Next day same month"),
                R("R7", {"C2": T, "C5": T}, "Next day same month"),
                R("R8", {"C2": T, "C6": T}, "Next day same month"),
                R("R9", {"C2": T, "C7": T}, "Next day same month"),
                R("R10", {"C2": T, "C4": F, "C5": F, "C6": F, "C7": F}, "First day of next month"),
                R("R11", {"C3": T, "C4": T}, "Next day same month"),
                R("R12", {"C3": T, "C5": T}, "Next day same month"),
                R("R13", {"C3": T, "C6": T}, "Next day same month"),
                R("R14", {"C3": T, "C7": T}, "Next day same month"),
                R("R15", {"C3": T, "C4": F, "C5": F, "C6": F, "C7": F}, "First day of next year"),
                R("R16", {"C1": F, "C2": F, "C3": F, "C4": T}, "Next day same month"),
                R("R17", {"C1": F, "C2": F, "C3": F, "C5": T, "C8": T}, "Next day same month"),
                R("R18", {"C1": F, "C2": F, "C3": F, "C5": T, "C8": F}, "First day of next month"),
                R("R19", {"C1": F, "C2": F, "C3": F, "C6": T, "C8": T}, "First day of next month"),
                R("R20", {"C1": F, "C2": F, "C3": F, "C6": T, "C8": F}, "Invalid date"),
                R("R21", {"C1": F, "C2": F, "C3": F, "C7": T}, "Invalid date"),
                R("R22", {"C1": F, "C2": F, "C3": F, "C4": F, "C5": F, "C6": F, "C7": F}, "Invalid date"),
            ],
        },
        reference="s02_nextdate", tags=("many rules", "leap-year logic", "invalid dates"),
        extra_probes=_nextdate_extra,
    ),
    Spec(
        id="S03", name="Order discount", category="Business rules (authored)",
        source="Authored; adapted from the order-total module of the authors' earlier STQA experiment",
        source_url="",
        rules_text=(
            "An online store computes the discount on an order. The base discount depends on the cart value: 5% "
            "for a cart value of Rs. 1000 or more, 10% for Rs. 2000 or more, and 20% for Rs. 5000 or more; only the "
            "highest applicable tier is used, and a cart value below Rs. 1000 gets no base discount. A valid "
            "coupon adds 10 percentage points and a loyalty member gets 5 more percentage points. The total "
            "discount can never exceed 30%. If the customer enters an invalid coupon, the order is rejected and "
            "the output is \"REJECTED\" whatever the other inputs are."),
        inputs=[Var("cart_value", "int", 0, 20000, desc="rupees"),
                Var("coupon", "enum", values=("none", "valid", "invalid")),
                Var("member", "bool", desc="loyalty-programme member")],
        output_name="discount", output_type="enum",
        output_values=("0%", "5%", "10%", "15%", "20%", "25%", "30%", "REJECTED"),
        gt_table={
            "conditions": [C("C1", "coupon == 'invalid'"), C("C2", "cart_value >= 5000"),
                           C("C3", "cart_value >= 2000"), C("C4", "cart_value >= 1000"),
                           C("C5", "coupon == 'valid'"), C("C6", "member")],
            "rules": [
                R("R1", {"C1": T}, "REJECTED"),
                R("R2", {"C1": F, "C2": T, "C5": F, "C6": F}, "20%"),
                R("R3", {"C1": F, "C2": T, "C5": F, "C6": T}, "25%"),
                R("R4", {"C1": F, "C2": T, "C5": T, "C6": F}, "30%"),
                R("R5", {"C1": F, "C2": T, "C5": T, "C6": T}, "30%"),
                R("R6", {"C1": F, "C2": F, "C3": T, "C5": F, "C6": F}, "10%"),
                R("R7", {"C1": F, "C2": F, "C3": T, "C5": F, "C6": T}, "15%"),
                R("R8", {"C1": F, "C2": F, "C3": T, "C5": T, "C6": F}, "20%"),
                R("R9", {"C1": F, "C2": F, "C3": T, "C5": T, "C6": T}, "25%"),
                R("R10", {"C1": F, "C3": F, "C4": T, "C5": F, "C6": F}, "5%"),
                R("R11", {"C1": F, "C3": F, "C4": T, "C5": F, "C6": T}, "10%"),
                R("R12", {"C1": F, "C3": F, "C4": T, "C5": T, "C6": F}, "15%"),
                R("R13", {"C1": F, "C3": F, "C4": T, "C5": T, "C6": T}, "20%"),
                R("R14", {"C1": F, "C4": F, "C5": F, "C6": F}, "0%"),
                R("R15", {"C1": F, "C4": F, "C5": F, "C6": T}, "5%"),
                R("R16", {"C1": F, "C4": F, "C5": T, "C6": F}, "10%"),
                R("R17", {"C1": F, "C4": F, "C5": T, "C6": T}, "15%"),
            ],
        },
        reference="s03_discount", tags=("tiers", "cap", "error rule"),
    ),
    Spec(
        id="S04", name="BMI level", category="GPT-DMN", source=GPT_DMN + " (description 'BMI', verbatim)",
        source_url=GPT_DMN_URL,
        rules_text=(
            "The BMI of a person can be calculated based on weight in kgs and length of a person in meters by using "
            "the following formula: weight/(length*length). If the BMI value is above 30, then the BMI-level is "
            "considered Obese. If you are a male and the BMI-value is under 18.5 then the BMI-level is severely "
            "underweight and if you are female, then you are considered underweight with the same bmi-value. If the "
            "BMI-value is between 18.5 and 25 (without 25), then the BMI-level is underweight for a male and normal "
            "for a female. Lastly, if the BMI-value is between 25 and 30 and you are a Male then the BMI-level is "
            "normal but if you are a female then BMI-level is overweight."),
        inputs=[Var("gender", "enum", values=("male", "female")),
                Var("weight", "float", 30.0, 200.0, desc="kg"), Var("length", "float", 1.4, 2.2, desc="m")],
        output_name="bmi_level", output_type="enum",
        output_values=("Severely underweight", "Underweight", "Normal", "Overweight", "Obese"),
        gt_table={
            "conditions": [C("C1", "weight / (length * length) > 30"), C("C2", "weight / (length * length) >= 25"),
                           C("C3", "weight / (length * length) >= 18.5"), C("C4", "gender == 'male'")],
            "rules": [
                R("R1", {"C1": T}, "Obese"),
                R("R2", {"C1": F, "C2": T, "C4": T}, "Normal"),
                R("R3", {"C1": F, "C2": T, "C4": F}, "Overweight"),
                R("R4", {"C2": F, "C3": T, "C4": T}, "Underweight"),
                R("R5", {"C2": F, "C3": T, "C4": F}, "Normal"),
                R("R6", {"C3": F, "C4": T}, "Severely underweight"),
                R("R7", {"C3": F, "C4": F}, "Underweight"),
            ],
        },
        reference="s04_bmi", tags=("computed quantity", "decimal boundaries"), extra_probes=_bmi_extra,
    ),
    Spec(
        id="S05", name="Pet adoption", category="GPT-DMN", source=GPT_DMN + " (description 'Determine pet', verbatim)",
        source_url=GPT_DMN_URL,
        rules_text=(
            "A couple is planning their future and is determining under which conditions a certain pet is adopted. "
            "Together they decided that if someone has allergies and that no one has  time to take care of a pet "
            "then that no pet is adopted. The couple also decided to not take in an animal if they don't have kids, "
            "don't have time even if they don't have allergies. However, if they have a an average amount of time "
            "available or a lot and even if they have allergies then they want to take in a fish. The couple decides "
            "that they also want a fish if they have kids, no allergies even if they don't have a lot of time "
            "available. The couple decides to take in a cat or a dog only if no one has allergies. A dog is taken in "
            "if they have a garden, kids and they have a lot of time. The dog is also adopted if they have a garden, "
            "no kids and have normal or a lot of time to spare. In all the remaining cases, the couple decides they "
            "want to have a cat."),
        inputs=[Var("allergies", "bool", desc="someone in the couple has allergies"),
                Var("time", "enum", values=("none", "average", "a lot"), desc="time available for a pet"),
                Var("kids", "bool"), Var("garden", "bool")],
        output_name="pet", output_type="enum", output_values=("No pet", "Fish", "Cat", "Dog"),
        gt_table={
            "conditions": [C("C1", "allergies"), C("C2", "time == 'none'"), C("C3", "time == 'a lot'"),
                           C("C4", "kids"), C("C5", "garden")],
            "rules": [
                R("R1", {"C1": T, "C2": T}, "No pet"),
                R("R2", {"C1": T, "C2": F}, "Fish"),
                R("R3", {"C1": F, "C2": T, "C4": F}, "No pet"),
                R("R4", {"C1": F, "C3": F, "C4": T}, "Fish"),
                R("R5", {"C1": F, "C2": F, "C3": F, "C4": F, "C5": T}, "Dog"),
                R("R6", {"C1": F, "C2": F, "C3": F, "C4": F, "C5": F}, "Cat"),
                R("R7", {"C1": F, "C3": T, "C5": T}, "Dog"),
                R("R8", {"C1": F, "C3": T, "C5": F}, "Cat"),
            ],
        },
        reference="s05_pet", tags=("enumerations", "default rule", "ambiguous wording"),
        clarifications=("Text kept verbatim. Interpretation used for the ground truth: 'even if they don't have a "
                        "lot of time' means time is none or average."),
    ),
    Spec(
        id="S06", name="Driver's licence", category="GPT-DMN",
        source=GPT_DMN + " (description \"Driver's license\", verbatim)", source_url=GPT_DMN_URL,
        rules_text=(
            "A person is eligible to get their driver's license based on their age, on being a national resident "
            "and if they have sufficient practical skills. The practical skills are evaluated based on the "
            "theoretical knowledge, driving skills, maneuvring skills and anticipation capabilities. Each of these "
            "aspects are evaluated with 'Excellent', 'Good' or 'Fail'. A person only passes the practical skills if "
            "they have no fails on any of the 4 aspects making up the practical skills. A person can only receive "
            "their driver's license if they are 18 or more, are a national resident and passed their practical "
            "skills test."),
        inputs=[Var("age", "int", 14, 90), Var("national_resident", "bool"),
                Var("theory", "enum", values=("Excellent", "Good", "Fail")),
                Var("driving", "enum", values=("Excellent", "Good", "Fail")),
                Var("maneuvering", "enum", values=("Excellent", "Good", "Fail")),
                Var("anticipation", "enum", values=("Excellent", "Good", "Fail"))],
        output_name="licence", output_type="enum", output_values=("Eligible", "Not eligible"),
        gt_table={
            "conditions": [C("C1", "age >= 18"), C("C2", "national_resident"), C("C3", "theory == 'Fail'"),
                           C("C4", "driving == 'Fail'"), C("C5", "maneuvering == 'Fail'"),
                           C("C6", "anticipation == 'Fail'")],
            "rules": [
                R("R1", {"C1": F}, "Not eligible"),
                R("R2", {"C1": T, "C2": F}, "Not eligible"),
                R("R3", {"C1": T, "C2": T, "C3": T}, "Not eligible"),
                R("R4", {"C1": T, "C2": T, "C3": F, "C4": T}, "Not eligible"),
                R("R5", {"C1": T, "C2": T, "C3": F, "C4": F, "C5": T}, "Not eligible"),
                R("R6", {"C1": T, "C2": T, "C3": F, "C4": F, "C5": F, "C6": T}, "Not eligible"),
                R("R7", {"C1": T, "C2": T, "C3": F, "C4": F, "C5": F, "C6": F}, "Eligible"),
            ],
        },
        reference="s06_licence", tags=("many inputs", "conjunction"),
        clarifications="Output labels ('Eligible', 'Not eligible') defined in the data dictionary.",
        extra_probes=_licence_extra,
    ),
    Spec(
        id="S07", name="Vacation days", category="GPT-DMN",
        source=GPT_DMN + " (description 'Holidays', verbatim); originally DMCommunity challenge Jan 2016 (J. Vanthienen)",
        source_url=GPT_DMN_URL + " ; https://dmcommunity.org/challenge/challenge-jan-2016/",
        rules_text=(
            "Every employee receives at least 22 days. Additional days are provided according to the following "
            "criteria: Only employees younger than 18 or at least 60 years, or employees with at least 30 years of "
            "service will receive 5 extra days. Employees with at least 30 years of service and also employees of "
            "age 60 or more, receive 3 extra days, on top of possible additional days already given. If an employee "
            "has at least 15 but less than 30 years of service, 2 extra days are given. These 2 days are also "
            "provided for employees of age 45 or more. These 2 extra days can not be combined with the extra 5 days."),
        inputs=[Var("age", "int", 16, 70), Var("years_of_service", "int", 0, 54)],
        constraint="years_of_service <= age - 16",
        constraint_desc="years_of_service <= age - 16 (nobody starts working before 16)",
        output_name="vacation_days", output_type="int", output_values=(),
        gt_table={
            "conditions": [C("C1", "age < 18"), C("C2", "age >= 60"), C("C3", "years_of_service >= 30"),
                           C("C4", "age >= 45"), C("C5", "years_of_service >= 15")],
            "rules": [
                R("R1", {"C1": T}, 27),
                R("R2", {"C1": F, "C2": T}, 30),
                R("R3", {"C1": F, "C2": F, "C3": T}, 30),
                R("R4", {"C1": F, "C2": F, "C3": F, "C4": T}, 24),
                R("R5", {"C1": F, "C2": F, "C3": F, "C4": F, "C5": T}, 24),
                R("R6", {"C1": F, "C2": F, "C3": F, "C4": F, "C5": F}, 22),
            ],
        },
        reference="s07_vacation", tags=("overlapping clauses", "exception", "input constraint"),
        clarifications="Domain constraint years_of_service <= age - 16 added in the data dictionary.",
        extra_probes=_vacation_extra,
    ),
    Spec(
        id="S08", name="Mode of transportation", category="GPT-DMN",
        source=GPT_DMN + " (description 'mode of transportation'; three boundary phrases clarified)",
        source_url=GPT_DMN_URL,
        rules_text=(
            "A person has the possibility to chose out of three transportation modes: walking, bike and driving a "
            "car. This person makes their transportation mode choice based on the distance, weather and whether that "
            "person is in a hurry. If the distance is bigger or equal to 10 and the person is not in a hurry, then "
            "the bike chosen if it is sunny or cloudy and if it is rainy or freezing then the car is chosen. In any "
            "case if the distance is bigger or equal to 10 and the person is in a hurry then the model of "
            "transportation is car. For medium distances of at least 5 but less than 10 kilometers, if it is raining "
            "the car is chosen. For the same medium distance, if the person is in a hurry the car is chosen. Again "
            "for medium distances and there is no hurry to arrive, the bike chosen if it sunny or cloudy and if it "
            "is freezing then the car is chosen. For a distance of at least 2 but less than 5 kilometers, the car is "
            "chosen if it raining or if the person is in a hurry and it is sunny, cloudy or freezing outside, "
            "otherwise the bike is chosen. Finally for a small distance smaller than 2 kilometers, it the person is "
            "in a hurry the bike is chosen otherwise the person will go by foot."),
        inputs=[Var("distance", "float", 0.0, 50.0, desc="km"),
                Var("weather", "enum", values=("sunny", "cloudy", "rainy", "freezing")),
                Var("hurry", "bool", desc="the person is in a hurry")],
        output_name="mode", output_type="enum", output_values=("walk", "bike", "car"),
        gt_table={
            "conditions": [C("C1", "distance >= 10"), C("C2", "distance >= 5"), C("C3", "distance >= 2"),
                           C("C4", "hurry"), C("C5", "weather in ('sunny', 'cloudy')"),
                           C("C6", "weather == 'rainy'"), C("C7", "weather == 'freezing'")],
            "rules": [
                R("R1", {"C1": T, "C4": F, "C5": T}, "bike"),
                R("R2", {"C1": T, "C4": F, "C5": F}, "car"),
                R("R3", {"C1": T, "C4": T}, "car"),
                R("R4", {"C1": F, "C2": T, "C6": T}, "car"),
                R("R5", {"C1": F, "C2": T, "C4": T, "C6": F}, "car"),
                R("R6", {"C1": F, "C2": T, "C4": F, "C5": T}, "bike"),
                R("R7", {"C1": F, "C2": T, "C4": F, "C7": T}, "car"),
                R("R8", {"C2": F, "C3": T, "C6": T}, "car"),
                R("R9", {"C2": F, "C3": T, "C4": T, "C6": F}, "car"),
                R("R10", {"C2": F, "C3": T, "C4": F, "C6": F}, "bike"),
                R("R11", {"C3": F, "C4": T}, "bike"),
                R("R12", {"C3": F, "C4": F}, "walk"),
            ],
        },
        reference="s08_transport", tags=("distance bands", "enumerations", "clarified boundaries"),
        clarifications=("Original boundary phrases replaced: 'more than 10' -> 'bigger or equal to 10'; "
                        "'between 5 and 10 kilometers' -> 'of at least 5 but less than 10 kilometers'; "
                        "'between 2 and 5 kilometers' -> 'of at least 2 but less than 5 kilometers'. "
                        "Without these edits the original text leaves distance 10 with hurry uncovered and "
                        "gives conflicting answers at exactly 5 km in freezing weather."),
    ),
    Spec(
        id="S09", name="Scholarship eligibility", category="GPT-DMN",
        source=GPT_DMN + " (description 'scholarship', verbatim)", source_url=GPT_DMN_URL,
        rules_text=(
            "An institution decides to distribute scholarships but can obviously not give them to everyone. "
            "Therefore, they decide to distribute them based on the grades, annual income and whether that person "
            "already received any scholarships for the year they are applying to. In short a person can only be "
            "eligible for a scholarship if the grades are excellent or good, they earn less than 50000 a year and "
            "have not received any other scholarship yet. All the other cases make that the person is not eligible "
            "for that scholarship."),
        inputs=[Var("grades", "enum", values=("excellent", "good", "average", "poor")),
                Var("annual_income", "int", 0, 200000),
                Var("received_other_scholarship", "bool")],
        output_name="scholarship", output_type="enum", output_values=("Eligible", "Not eligible"),
        gt_table={
            "conditions": [C("C1", "grades in ('excellent', 'good')"), C("C2", "annual_income < 50000"),
                           C("C3", "received_other_scholarship")],
            "rules": [
                R("R1", {"C1": F}, "Not eligible"),
                R("R2", {"C1": T, "C2": F}, "Not eligible"),
                R("R3", {"C1": T, "C2": T, "C3": T}, "Not eligible"),
                R("R4", {"C1": T, "C2": T, "C3": F}, "Eligible"),
            ],
        },
        reference="s09_scholarship", tags=("conjunction", "small"),
        clarifications="Grade values (excellent, good, average, poor) and output labels defined in the data dictionary.",
    ),
    Spec(
        id="S10", name="Login with lockout and OTP", category="Business rules (authored)",
        source="Authored for this benchmark", source_url="",
        rules_text=(
            "A web application evaluates every login attempt. If the account is already locked, the result is "
            "\"Account locked\", whatever else is true. For an account that is not locked, a wrong password gives "
            "\"Invalid credentials\", except that when the account already has 4 or more consecutive failed "
            "attempts, the wrong password locks the account and the result is \"Account locked\". If the password is "
            "correct and the login comes from a trusted device, the result is \"Access granted\". If the password is "
            "correct but the device is not trusted, the user must pass a one-time password (OTP) check: when the OTP "
            "has been verified the result is \"Access granted\", otherwise it is \"OTP required\"."),
        inputs=[Var("account_locked", "bool"), Var("password_correct", "bool"),
                Var("failed_attempts", "int", 0, 9, desc="consecutive failed attempts before this one"),
                Var("trusted_device", "bool"), Var("otp_verified", "bool")],
        output_name="result", output_type="enum",
        output_values=("Access granted", "Invalid credentials", "Account locked", "OTP required"),
        gt_table={
            "conditions": [C("C1", "account_locked"), C("C2", "password_correct"), C("C3", "failed_attempts >= 4"),
                           C("C4", "trusted_device"), C("C5", "otp_verified")],
            "rules": [
                R("R1", {"C1": T}, "Account locked"),
                R("R2", {"C1": F, "C2": F, "C3": F}, "Invalid credentials"),
                R("R3", {"C1": F, "C2": F, "C3": T}, "Account locked"),
                R("R4", {"C1": F, "C2": T, "C4": T}, "Access granted"),
                R("R5", {"C1": F, "C2": T, "C4": F, "C5": T}, "Access granted"),
                R("R6", {"C1": F, "C2": T, "C4": F, "C5": F}, "OTP required"),
            ],
        },
        reference="s10_login", tags=("security", "precedence", "threshold"), extra_probes=_login_extra,
    ),
    Spec(
        id="S11", name="UPI transfer screening", category="Business rules (authored)",
        source="Authored for this benchmark (simplified; not an official NPCI rule set)", source_url="",
        rules_text=(
            "A payment app screens every UPI money transfer before sending it. A transfer of more than Rs. 100000 is "
            "blocked because it exceeds the per-transaction limit, and the output is \"Blocked\". Otherwise, a "
            "transfer to a new payee (a payee added less than 24 hours ago) is put \"On hold\" if the amount is more "
            "than Rs. 5000. In all other cases, if the user is not on their registered device and the amount is more "
            "than Rs. 2000, the app asks for an OTP and the output is \"OTP required\". Every remaining transfer is "
            "\"Allowed\"."),
        inputs=[Var("amount", "int", 1, 200000, desc="rupees"), Var("new_payee", "bool"),
                Var("registered_device", "bool")],
        output_name="decision", output_type="enum",
        output_values=("Blocked", "On hold", "OTP required", "Allowed"),
        gt_table={
            "conditions": [C("C1", "amount > 100000"), C("C2", "new_payee"), C("C3", "amount > 5000"),
                           C("C4", "registered_device"), C("C5", "amount > 2000")],
            "rules": [
                R("R1", {"C1": T}, "Blocked"),
                R("R2", {"C1": F, "C2": T, "C3": T}, "On hold"),
                R("R3", {"C1": F, "C2": T, "C3": F, "C4": F, "C5": T}, "OTP required"),
                R("R4", {"C1": F, "C2": T, "C3": F, "C4": F, "C5": F}, "Allowed"),
                R("R5", {"C1": F, "C2": T, "C3": F, "C4": T}, "Allowed"),
                R("R6", {"C1": F, "C2": F, "C4": F, "C5": T}, "OTP required"),
                R("R7", {"C1": F, "C2": F, "C4": F, "C5": F}, "Allowed"),
                R("R8", {"C1": F, "C2": F, "C4": T}, "Allowed"),
            ],
        },
        reference="s11_upi", tags=("thresholds", "precedence", "payments"),
    ),
    Spec(
        id="S12", name="Personal-loan screening", category="Business rules (authored)",
        source="Authored for this benchmark", source_url="",
        rules_text=(
            "A bank screens personal-loan applications. Applicants younger than 21 years are \"Rejected\". Applicants "
            "aged 21 or more are assessed on their credit score: a score below 600 is \"Rejected\" and a score of 750 "
            "or above is \"Approved\". For a credit score from 600 to 749, the application is \"Approved\" if the "
            "monthly income is at least Rs. 50000; if the income is lower, the application is \"Approved\" only when "
            "there is a co-signer, and otherwise it is \"Referred\" to a loan officer."),
        inputs=[Var("age", "int", 18, 75), Var("credit_score", "int", 300, 900),
                Var("monthly_income", "int", 0, 500000, desc="rupees"), Var("has_cosigner", "bool")],
        output_name="decision", output_type="enum", output_values=("Approved", "Rejected", "Referred"),
        gt_table={
            "conditions": [C("C1", "age < 21"), C("C2", "credit_score < 600"), C("C3", "credit_score >= 750"),
                           C("C4", "monthly_income >= 50000"), C("C5", "has_cosigner")],
            "rules": [
                R("R1", {"C1": T}, "Rejected"),
                R("R2", {"C1": F, "C2": T}, "Rejected"),
                R("R3", {"C1": F, "C3": T}, "Approved"),
                R("R4", {"C1": F, "C2": F, "C3": F, "C4": T}, "Approved"),
                R("R5", {"C1": F, "C2": F, "C3": F, "C4": F, "C5": T}, "Approved"),
                R("R6", {"C1": F, "C2": F, "C3": F, "C4": F, "C5": F}, "Referred"),
            ],
        },
        reference="s12_loan", tags=("thresholds", "precedence", "finance"),
    ),
]

SPEC_BY_ID = {s.id: s for s in SPECS}
