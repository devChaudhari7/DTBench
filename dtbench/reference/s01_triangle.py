"""S01 Triangle classification (Jorgensen 2013, ch. 7; Myers et al. 2011)."""


def decide(a, b, c):
    if a >= b + c or b >= a + c or c >= a + b:
        return "Not a triangle"
    if a == b and b == c:
        return "Equilateral"
    if a == b or b == c or a == c:
        return "Isosceles"
    return "Scalene"
