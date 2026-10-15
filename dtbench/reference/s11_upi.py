"""S11 UPI transfer screening (authored for this benchmark; simplified, not an NPCI rule set)."""


def decide(amount, new_payee, registered_device):
    if amount > 100000:
        return "Blocked"
    if new_payee and amount > 5000:
        return "On hold"
    if not registered_device and amount > 2000:
        return "OTP required"
    return "Allowed"
