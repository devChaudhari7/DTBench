"""Independent reference implementations (one per benchmark spec).

Each module defines ``decide(**inputs)`` written the way a developer would code
the business rules. They serve as the test oracle and as the subject of
mutation analysis. They were written separately from the ground-truth tables
and both are cross-checked on every evaluation probe (scripts/verify_benchmark.py).
"""
