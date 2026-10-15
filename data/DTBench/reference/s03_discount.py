"""S03 Order discount with tiers, coupon, membership and a 30% cap."""


def decide(cart_value, coupon, member):
    if coupon == "invalid":
        return "REJECTED"
    if cart_value >= 5000:
        rate = 20
    elif cart_value >= 2000:
        rate = 10
    elif cart_value >= 1000:
        rate = 5
    else:
        rate = 0
    if coupon == "valid":
        rate = rate + 10
    if member:
        rate = rate + 5
    if rate > 30:
        rate = 30
    return str(rate) + "%"
