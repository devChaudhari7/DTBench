# DTBench ground-truth decision tables

T = condition true, F = false, - = don't care. Each column is one rule.


## S01 Triangle classification

Source: P. C. Jorgensen, Software Testing: A Craftsman's Approach, 4th ed., CRC Press, 2013, ch. 7; G. J. Myers et al., The Art of Software Testing, 3rd ed., Wiley, 2011

Output: `triangle_type`

| Condition | R1 | R2 | R3 | R4 | R5 | R6 | R7 | R8 |
|---|---|---|---|---|---|---|---|---|
| C1: `a < b + c` | F | T | T | T | T | T | T | T |
| C2: `b < a + c` | - | F | T | T | T | T | T | T |
| C3: `c < a + b` | - | - | F | T | T | T | T | T |
| C4: `a == b` | - | - | - | T | T | F | F | F |
| C5: `a == c` | - | - | - | T | F | T | F | F |
| C6: `b == c` | - | - | - | T | F | F | T | F |
| **Output** | Not a triangle | Not a triangle | Not a triangle | Equilateral | Isosceles | Isosceles | Isosceles | Scalene |

Infeasible combinations (not counted): C1=T, C2=T, C3=T, C4=T, C5=T, C6=F (a=b and a=c imply b=c); C1=T, C2=T, C3=T, C4=T, C5=F, C6=T (a=b and b=c imply a=c); C1=T, C2=T, C3=T, C4=F, C5=T, C6=T (a=c and b=c imply a=b)


## S02 NextDate

Source: P. C. Jorgensen, Software Testing: A Craftsman's Approach, 4th ed., CRC Press, 2013, ch. 7

Output: `next_date_action`

| Condition | R1 | R2 | R3 | R4 | R5 | R6 | R7 | R8 | R9 | R10 | R11 | R12 | R13 | R14 | R15 | R16 | R17 | R18 | R19 | R20 | R21 | R22 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1: `month in (4, 6, 9, 11)` | T | T | T | T | T | - | - | - | - | - | - | - | - | - | - | F | F | F | F | F | F | F |
| C2: `month in (1, 3, 5, 7, 8, 10)` | - | - | - | - | - | T | T | T | T | T | - | - | - | - | - | F | F | F | F | F | F | F |
| C3: `month == 12` | - | - | - | - | - | - | - | - | - | - | T | T | T | T | T | F | F | F | F | F | F | F |
| C4: `day <= 27` | T | - | - | - | F | T | - | - | - | F | T | - | - | - | F | T | - | - | - | - | - | F |
| C5: `day == 28` | - | T | - | - | F | - | T | - | - | F | - | T | - | - | F | - | T | T | - | - | - | F |
| C6: `day == 29` | - | - | T | - | F | - | - | T | - | F | - | - | T | - | F | - | - | - | T | T | - | F |
| C7: `day == 30` | - | - | - | T | F | - | - | - | T | F | - | - | - | T | F | - | - | - | - | - | T | F |
| C8: `(year % 4 == 0 and year % 100 != 0) or year % 400 == 0` | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | T | F | T | F | - | - |
| **Output** | Next day same month | Next day same month | Next day same month | First day of next month | Invalid date | Next day same month | Next day same month | Next day same month | Next day same month | First day of next month | Next day same month | Next day same month | Next day same month | Next day same month | First day of next year | Next day same month | Next day same month | First day of next month | First day of next month | Invalid date | Invalid date | Invalid date |


## S03 Order discount

Source: Authored; adapted from the order-total module of the authors' earlier STQA experiment

Output: `discount`

| Condition | R1 | R2 | R3 | R4 | R5 | R6 | R7 | R8 | R9 | R10 | R11 | R12 | R13 | R14 | R15 | R16 | R17 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1: `coupon == 'invalid'` | T | F | F | F | F | F | F | F | F | F | F | F | F | F | F | F | F |
| C2: `cart_value >= 5000` | - | T | T | T | T | F | F | F | F | - | - | - | - | - | - | - | - |
| C3: `cart_value >= 2000` | - | - | - | - | - | T | T | T | T | F | F | F | F | - | - | - | - |
| C4: `cart_value >= 1000` | - | - | - | - | - | - | - | - | - | T | T | T | T | F | F | F | F |
| C5: `coupon == 'valid'` | - | F | F | T | T | F | F | T | T | F | F | T | T | F | F | T | T |
| C6: `member` | - | F | T | F | T | F | T | F | T | F | T | F | T | F | T | F | T |
| **Output** | REJECTED | 20% | 25% | 30% | 30% | 10% | 15% | 20% | 25% | 5% | 10% | 15% | 20% | 0% | 5% | 10% | 15% |


## S04 BMI level

Source: A. Goossens, S. Vandevelde, J. Vanthienen and J. Vennekens, "GPT-3 for Decision Logic Modeling", RuleML+RR 2023 Companion, CEUR-WS Vol. 3485 (description 'BMI', verbatim)

Output: `bmi_level`

| Condition | R1 | R2 | R3 | R4 | R5 | R6 | R7 |
|---|---|---|---|---|---|---|---|
| C1: `weight / (length * length) > 30` | T | F | F | - | - | - | - |
| C2: `weight / (length * length) >= 25` | - | T | T | F | F | - | - |
| C3: `weight / (length * length) >= 18.5` | - | - | - | T | T | F | F |
| C4: `gender == 'male'` | - | T | F | T | F | T | F |
| **Output** | Obese | Normal | Overweight | Underweight | Normal | Severely underweight | Underweight |


## S05 Pet adoption

Source: A. Goossens, S. Vandevelde, J. Vanthienen and J. Vennekens, "GPT-3 for Decision Logic Modeling", RuleML+RR 2023 Companion, CEUR-WS Vol. 3485 (description 'Determine pet', verbatim)

Output: `pet`

| Condition | R1 | R2 | R3 | R4 | R5 | R6 | R7 | R8 |
|---|---|---|---|---|---|---|---|---|
| C1: `allergies` | T | T | F | F | F | F | F | F |
| C2: `time == 'none'` | T | F | T | - | F | F | - | - |
| C3: `time == 'a lot'` | - | - | - | F | F | F | T | T |
| C4: `kids` | - | - | F | T | F | F | - | - |
| C5: `garden` | - | - | - | - | T | F | T | F |
| **Output** | No pet | Fish | No pet | Fish | Dog | Cat | Dog | Cat |


## S06 Driver's licence

Source: A. Goossens, S. Vandevelde, J. Vanthienen and J. Vennekens, "GPT-3 for Decision Logic Modeling", RuleML+RR 2023 Companion, CEUR-WS Vol. 3485 (description "Driver's license", verbatim)

Output: `licence`

| Condition | R1 | R2 | R3 | R4 | R5 | R6 | R7 |
|---|---|---|---|---|---|---|---|
| C1: `age >= 18` | F | T | T | T | T | T | T |
| C2: `national_resident` | - | F | T | T | T | T | T |
| C3: `theory == 'Fail'` | - | - | T | F | F | F | F |
| C4: `driving == 'Fail'` | - | - | - | T | F | F | F |
| C5: `maneuvering == 'Fail'` | - | - | - | - | T | F | F |
| C6: `anticipation == 'Fail'` | - | - | - | - | - | T | F |
| **Output** | Not eligible | Not eligible | Not eligible | Not eligible | Not eligible | Not eligible | Eligible |


## S07 Vacation days

Source: A. Goossens, S. Vandevelde, J. Vanthienen and J. Vennekens, "GPT-3 for Decision Logic Modeling", RuleML+RR 2023 Companion, CEUR-WS Vol. 3485 (description 'Holidays', verbatim); originally DMCommunity challenge Jan 2016 (J. Vanthienen)

Output: `vacation_days`

| Condition | R1 | R2 | R3 | R4 | R5 | R6 |
|---|---|---|---|---|---|---|
| C1: `age < 18` | T | F | F | F | F | F |
| C2: `age >= 60` | - | T | F | F | F | F |
| C3: `years_of_service >= 30` | - | - | T | F | F | F |
| C4: `age >= 45` | - | - | - | T | F | F |
| C5: `years_of_service >= 15` | - | - | - | - | T | F |
| **Output** | 27 | 30 | 30 | 24 | 24 | 22 |


## S08 Mode of transportation

Source: A. Goossens, S. Vandevelde, J. Vanthienen and J. Vennekens, "GPT-3 for Decision Logic Modeling", RuleML+RR 2023 Companion, CEUR-WS Vol. 3485 (description 'mode of transportation'; three boundary phrases clarified)

Output: `mode`

| Condition | R1 | R2 | R3 | R4 | R5 | R6 | R7 | R8 | R9 | R10 | R11 | R12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1: `distance >= 10` | T | T | T | F | F | F | F | - | - | - | - | - |
| C2: `distance >= 5` | - | - | - | T | T | T | T | F | F | F | - | - |
| C3: `distance >= 2` | - | - | - | - | - | - | - | T | T | T | F | F |
| C4: `hurry` | F | F | T | - | T | F | F | - | T | F | T | F |
| C5: `weather in ('sunny', 'cloudy')` | T | F | - | - | - | T | - | - | - | - | - | - |
| C6: `weather == 'rainy'` | - | - | - | T | F | - | - | T | F | F | - | - |
| C7: `weather == 'freezing'` | - | - | - | - | - | - | T | - | - | - | - | - |
| **Output** | bike | car | car | car | car | bike | car | car | car | bike | bike | walk |


## S09 Scholarship eligibility

Source: A. Goossens, S. Vandevelde, J. Vanthienen and J. Vennekens, "GPT-3 for Decision Logic Modeling", RuleML+RR 2023 Companion, CEUR-WS Vol. 3485 (description 'scholarship', verbatim)

Output: `scholarship`

| Condition | R1 | R2 | R3 | R4 |
|---|---|---|---|---|
| C1: `grades in ('excellent', 'good')` | F | T | T | T |
| C2: `annual_income < 50000` | - | F | T | T |
| C3: `received_other_scholarship` | - | - | T | F |
| **Output** | Not eligible | Not eligible | Not eligible | Eligible |


## S10 Login with lockout and OTP

Source: Authored for this benchmark

Output: `result`

| Condition | R1 | R2 | R3 | R4 | R5 | R6 |
|---|---|---|---|---|---|---|
| C1: `account_locked` | T | F | F | F | F | F |
| C2: `password_correct` | - | F | F | T | T | T |
| C3: `failed_attempts >= 4` | - | F | T | - | - | - |
| C4: `trusted_device` | - | - | - | T | F | F |
| C5: `otp_verified` | - | - | - | - | T | F |
| **Output** | Account locked | Invalid credentials | Account locked | Access granted | Access granted | OTP required |


## S11 UPI transfer screening

Source: Authored for this benchmark (simplified; not an official NPCI rule set)

Output: `decision`

| Condition | R1 | R2 | R3 | R4 | R5 | R6 | R7 | R8 |
|---|---|---|---|---|---|---|---|---|
| C1: `amount > 100000` | T | F | F | F | F | F | F | F |
| C2: `new_payee` | - | T | T | T | T | F | F | F |
| C3: `amount > 5000` | - | T | F | F | F | - | - | - |
| C4: `registered_device` | - | - | F | F | T | F | F | T |
| C5: `amount > 2000` | - | - | T | F | - | T | F | - |
| **Output** | Blocked | On hold | OTP required | Allowed | Allowed | OTP required | Allowed | Allowed |


## S12 Personal-loan screening

Source: Authored for this benchmark

Output: `decision`

| Condition | R1 | R2 | R3 | R4 | R5 | R6 |
|---|---|---|---|---|---|---|
| C1: `age < 21` | T | F | F | F | F | F |
| C2: `credit_score < 600` | - | T | - | F | F | F |
| C3: `credit_score >= 750` | - | - | T | F | F | F |
| C4: `monthly_income >= 50000` | - | - | - | T | F | F |
| C5: `has_cosigner` | - | - | - | - | T | F |
| **Output** | Rejected | Rejected | Approved | Approved | Approved | Referred |
