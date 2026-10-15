"""S10 Login attempt with account lockout and OTP (authored for this benchmark)."""

MAX_FAILED = 4


def decide(account_locked, password_correct, failed_attempts, trusted_device, otp_verified):
    if account_locked:
        return "Account locked"
    if not password_correct:
        if failed_attempts >= MAX_FAILED:
            return "Account locked"
        return "Invalid credentials"
    if trusted_device or otp_verified:
        return "Access granted"
    return "OTP required"
