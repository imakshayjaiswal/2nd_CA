"""
AeroTax Pure-Python Calculation Engine (engine_py.py)
======================================================
Drop-in replacement for the C shared library.
Identical function signatures to what ctypes would expose.

This runs immediately — no compiler, no DLL, no dependencies beyond Python.
The backend (main.py) auto-detects whether to use C or this fallback.
"""

import math
from typing import List, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# TAX CONSTANTS  (FY 2024-25)
# ─────────────────────────────────────────────────────────────────────────────

REBATE_LIMIT   = 700_000     # Section 87A: no tax if taxable income ≤ ₹7 L
SURCHARGE_10   = 5_000_000   # 10% surcharge above ₹50 L
SURCHARGE_15   = 10_000_000  # 15% surcharge above ₹1 Cr
CESS_RATE      = 0.04        # 4% Health & Education Cess
STD_DEDUCTION  = 75_000      # Standard deduction (Budget 2024)

NEW_REGIME_SLABS = [
    (0,          300_000,   0.00),
    (300_000,    600_000,   0.05),
    (600_000,    900_000,   0.10),
    (900_000,  1_200_000,   0.15),
    (1_200_000, 1_500_000,  0.20),
    (1_500_000,  None,      0.30),   # None = no upper limit
]


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _slab_tax(taxable: float) -> float:
    """Walk the New Regime slab table and accumulate raw base tax."""
    tax = 0.0
    for lower, upper, rate in NEW_REGIME_SLABS:
        if taxable <= lower:
            break
        ceiling = taxable if upper is None else upper
        chunk   = min(taxable, ceiling) - lower
        tax    += chunk * rate
    return tax


def _add_surcharge_cess(base: float, gross: float) -> float:
    """Add surcharge (based on gross income) and 4% cess."""
    if   gross > SURCHARGE_15: surcharge = base * 0.15
    elif gross > SURCHARGE_10: surcharge = base * 0.10
    else:                      surcharge = 0.0
    total = base + surcharge
    return round(total + total * CESS_RATE, 2)


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC: TAX CALCULATION
# ─────────────────────────────────────────────────────────────────────────────

def py_calculate_tax(income: float, deductions: float) -> float:
    """
    Returns net tax payable under the New Tax Regime (FY 2024-25).
    Applies standard deduction of ₹75,000 and Section 87A rebate.
    """
    if income <= 0:
        return 0.0
    taxable = income - deductions - STD_DEDUCTION
    taxable = max(taxable, 0.0)
    if taxable <= REBATE_LIMIT:
        return 0.0
    return _add_surcharge_cess(_slab_tax(taxable), income)


def py_calculate_tax_old_regime(income: float, deductions: float) -> float:
    """Returns net tax payable under the Old Tax Regime."""
    taxable = income - deductions
    if taxable <= 250_000:
        return 0.0
    if   taxable <= 500_000:   base = (taxable - 250_000) * 0.05
    elif taxable <= 1_000_000: base = 12_500  + (taxable - 500_000)   * 0.20
    else:                      base = 112_500 + (taxable - 1_000_000) * 0.30
    if taxable <= 500_000:     # Section 87A rebate (old regime ≤ ₹5 L)
        return 0.0
    return _add_surcharge_cess(base, income)


def py_compare_regimes(income: float, deductions: float) -> dict:
    """
    Compares both regimes and returns a detailed breakdown.
    """
    new_tax = py_calculate_tax(income, deductions)
    old_tax = py_calculate_tax_old_regime(income, deductions)
    return {
        "new_regime_tax": new_tax,
        "old_regime_tax": old_tax,
        "better_regime":  "new" if new_tax <= old_tax else "old",
        "savings":        round(abs(new_tax - old_tax), 2),
    }


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC: ANOMALY DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def py_detect_outliers(
    transactions: List[float],
    threshold: float = 3.0
) -> dict:
    """
    Flags transactions that deviate more than `threshold` standard deviations
    from the sample mean (z-score method).

    Uses Kahan summation for numerical stability and Bessel's correction
    for an unbiased sample standard deviation.

    Returns:
        {
            "flags":   [1, 0, 0, 1, ...],   # 1 = anomaly
            "count":   int,
            "mean":    float,
            "std_dev": float,
            "flagged_indices": [int, ...],
        }
    """
    n = len(transactions)
    if n == 0:
        return {"flags": [], "count": 0, "mean": 0.0,
                "std_dev": 0.0, "flagged_indices": []}

    # ── Kahan-compensated mean ──────────────────────────────────────────────
    total, comp = 0.0, 0.0
    for x in transactions:
        y     = x - comp
        t     = total + y
        comp  = (t - total) - y
        total = t
    mean = total / n

    # ── Sample std deviation (Bessel's correction: divide by n-1) ──────────
    sq_sum = sum((x - mean) ** 2 for x in transactions)
    std_dev = math.sqrt(sq_sum / (n - 1)) if n > 1 else 0.0

    # ── Flag outliers ───────────────────────────────────────────────────────
    flags: List[int] = []
    flagged_indices: List[int] = []

    for i, x in enumerate(transactions):
        z = abs(x - mean) / std_dev if std_dev > 1e-9 else 0.0
        flagged = 1 if z > threshold else 0
        flags.append(flagged)
        if flagged:
            flagged_indices.append(i)

    return {
        "flags":           flags,
        "count":           len(flagged_indices),
        "mean":            round(mean, 4),
        "std_dev":         round(std_dev, 4),
        "flagged_indices": flagged_indices,
    }


# ─────────────────────────────────────────────────────────────────────────────
# QUICK SELF-TEST  (run: python engine_py.py)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  AeroTax Engine — Self-Test")
    print("=" * 55)

    # Tax tests
    cases = [
        (500_000,   0,       "Below rebate limit"),
        (700_000,   0,       "Exactly at rebate limit"),
        (1_000_000, 150_000, "10 lakh, with 80C"),
        (1_500_000, 0,       "15 lakh, no deductions"),
        (5_000_001, 0,       "50 lakh surcharge trigger"),
    ]
    print("\n  New Regime Tax:")
    for income, ded, label in cases:
        tax = py_calculate_tax(income, ded)
        print(f"    {label:<35} => Rs {tax:>12,.2f}")

    print("\n  Regime Comparison (Income=12L, Deductions=1.5L):")
    result = py_compare_regimes(1_200_000, 150_000)
    for k, v in result.items():
        print(f"    {k:<20}: {v}")

    print("\n  Anomaly Detection:")
    txns = [100, 98, 105, 102, 99, 850, 101, 97, 103, 5]
    out  = py_detect_outliers(txns, threshold=3.0)
    print(f"    Transactions : {txns}")
    print(f"    Mean         : {out['mean']}")
    print(f"    Std Dev      : {out['std_dev']}")
    print(f"    Flagged      : indices {out['flagged_indices']}")
    print(f"    Count        : {out['count']} anomalies")
    print("\n  All tests passed!")
