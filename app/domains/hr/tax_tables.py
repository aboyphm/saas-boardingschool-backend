from __future__ import annotations

"""
PPh 21 TER (Tarif Efektif Rata-rata) tables based on Indonesian MoF PMK 168/2023.

Each table entry is a tuple of (upper_bound_exclusive, rate).
The last entry always has upper_bound = None, meaning "everything above".
Gross salary is the monthly gross in IDR.

TER-A applies to PTKP status TK/0 (single, no dependants).
TER-B applies to PTKP status K/0 or TK/1.
TER-C applies to PTKP status K/1 and above.
"""

from typing import Any

# ─── TER Tables (monthly gross salary → effective rate) ───────────────────────

# Format: list of (upper_bound_exclusive, rate)
# upper_bound = None means "and above"

TER_A: list[tuple[int | None, float]] = [
    (5_400_000, 0.00),
    (5_650_000, 0.0025),
    (5_950_000, 0.005),
    (6_300_000, 0.0075),
    (6_750_000, 0.01),
    (7_500_000, 0.0125),
    (8_550_000, 0.015),
    (9_650_000, 0.0175),
    (10_050_000, 0.02),
    (10_350_000, 0.0225),
    (10_700_000, 0.025),
    (11_050_000, 0.03),
    (11_600_000, 0.035),
    (12_500_000, 0.04),
    (13_750_000, 0.05),
    (15_100_000, 0.06),
    (16_950_000, 0.07),
    (19_750_000, 0.08),
    (24_150_000, 0.09),
    (26_450_000, 0.10),
    (28_000_000, 0.11),
    (30_050_000, 0.12),
    (32_400_000, 0.13),
    (35_400_000, 0.14),
    (39_100_000, 0.15),
    (43_850_000, 0.16),
    (47_800_000, 0.17),
    (51_400_000, 0.18),
    (56_300_000, 0.19),
    (62_200_000, 0.20),
    (None, 0.34),
]

TER_B: list[tuple[int | None, float]] = [
    (6_200_000, 0.00),
    (6_500_000, 0.0025),
    (6_850_000, 0.005),
    (7_300_000, 0.0075),
    (9_200_000, 0.01),
    (10_750_000, 0.015),
    (11_250_000, 0.0175),
    (11_600_000, 0.02),
    (12_600_000, 0.025),
    (13_600_000, 0.03),
    (14_950_000, 0.04),
    (16_400_000, 0.05),
    (18_450_000, 0.06),
    (21_850_000, 0.07),
    (26_000_000, 0.08),
    (27_700_000, 0.09),
    (29_350_000, 0.10),
    (31_450_000, 0.11),
    (33_950_000, 0.12),
    (37_100_000, 0.13),
    (41_100_000, 0.14),
    (45_800_000, 0.15),
    (49_500_000, 0.16),
    (53_800_000, 0.17),
    (58_500_000, 0.18),
    (64_000_000, 0.19),
    (None, 0.34),
]

TER_C: list[tuple[int | None, float]] = [
    (6_600_000, 0.00),
    (6_950_000, 0.0025),
    (7_350_000, 0.005),
    (7_800_000, 0.0075),
    (8_850_000, 0.01),
    (9_800_000, 0.015),
    (10_950_000, 0.0175),
    (11_200_000, 0.02),
    (12_050_000, 0.025),
    (12_950_000, 0.03),
    (14_150_000, 0.035),
    (15_550_000, 0.04),
    (17_050_000, 0.05),
    (19_500_000, 0.06),
    (22_700_000, 0.07),
    (26_600_000, 0.08),
    (28_100_000, 0.09),
    (30_100_000, 0.10),
    (32_600_000, 0.11),
    (35_400_000, 0.12),
    (38_900_000, 0.13),
    (43_000_000, 0.14),
    (47_400_000, 0.15),
    (51_200_000, 0.16),
    (55_800_000, 0.17),
    (60_400_000, 0.18),
    (66_700_000, 0.19),
    (None, 0.34),
]

# PTKP status → TER table mapping
_PTKP_TO_TABLE: dict[str, list[tuple[int | None, float]]] = {
    "TK/0": TER_A,
    "K/0": TER_B,
    "TK/1": TER_B,
    "K/1": TER_C,
    "K/2": TER_C,
    "K/3": TER_C,
}


def _lookup_ter_rate(gross: float, table: list[tuple[int | None, float]]) -> float:
    """Return the effective TER rate for the given monthly gross from a TER table."""
    for upper_bound, rate in table:
        if upper_bound is None or gross < upper_bound:
            return rate
    return table[-1][1]


def calculate_pph21(
    gross: float,
    employment_type: str,
    tax_config: dict[str, Any] | None,
) -> float:
    """
    Calculate monthly PPh 21 (Indonesian income tax) for an employee.

    Parameters
    ----------
    gross:
        Monthly gross salary in IDR (base_salary + allowances + one-time additions).
    employment_type:
        One of the EmploymentType enum string values.
    tax_config:
        Optional override dict from the contract's ``tax_config`` JSONB column.
        Shape: ``{"method": "exempt"}`` | ``{"method": "flat", "rate": 0.025}`` |
               ``{"method": "ter", "ptkp_status": "TK/0"}``
        When None, employment-type defaults apply.

    Returns
    -------
    float
        Tax amount in IDR (rounded to 2 decimal places).
    """
    if tax_config:
        method = tax_config.get("method", "ter")
        if method == "exempt":
            return 0.0
        if method == "flat":
            rate = float(tax_config.get("rate", 0.0))
            return round(gross * rate, 2)
        if method == "ter":
            ptkp_status = tax_config.get("ptkp_status", "TK/0")
            table = _PTKP_TO_TABLE.get(ptkp_status, TER_A)
            rate = _lookup_ter_rate(gross, table)
            return round(gross * rate, 2)

    # Employment-type defaults when no tax_config is set
    if employment_type in ("internship",):
        return 0.0

    if employment_type in ("full_time", "part_time"):
        # Default TER method, assume TK/0
        rate = _lookup_ter_rate(gross, TER_A)
        return round(gross * rate, 2)

    if employment_type in ("honorer", "honorary"):
        # Final PPh 21 Article 21: 0% if < 2.5M, else 2.5%
        return 0.0 if gross < 2_500_000 else round(gross * 0.025, 2)

    if employment_type == "freelance":
        return round(gross * 0.05, 2)

    # Fallback: treat as TK/0 TER
    rate = _lookup_ter_rate(gross, TER_A)
    return round(gross * rate, 2)


def calculate_bpjs_employee(
    gross: float,
    employment_type: str,
    insurance_config: dict[str, Any] | None,
) -> float:
    """
    Calculate the employee-side BPJS deduction.

    BPJS Kesehatan employee: 1%
    JHT (Jaminan Hari Tua) employee: 2%
    JP (Jaminan Pensiun) employee: 1%

    Total employee deduction = bpjs_kes_employee + jht_employee + jp_employee.
    Non-mandatory types (honorer, internship, freelance) default to 0 unless overridden.

    Returns
    -------
    float
        Total employee BPJS/insurance deduction in IDR.
    """
    defaults = _get_insurance_defaults(employment_type)

    if insurance_config:
        bpjs_kes = float(insurance_config.get("bpjs_kesehatan_employee", defaults["bpjs_kes_employee"]))
        jht = float(insurance_config.get("jht_employee", defaults["jht_employee"]))
        jp = float(insurance_config.get("jp_employee", defaults["jp_employee"]))
    else:
        bpjs_kes = defaults["bpjs_kes_employee"]
        jht = defaults["jht_employee"]
        jp = defaults["jp_employee"]

    return round(gross * (bpjs_kes + jht + jp), 2)


def calculate_bpjs_employer(
    gross: float,
    employment_type: str,
    insurance_config: dict[str, Any] | None,
) -> float:
    """
    Calculate the employer-side BPJS contribution (cost to institution, not deducted from net).

    BPJS Kesehatan employer: 4%
    JKK (Jaminan Kecelakaan Kerja) employer: 0.24% (standard rate)
    JKM (Jaminan Kematian) employer: 0.3%
    JHT employer: 3.7%
    JP employer: 2%

    Returns
    -------
    float
        Total employer BPJS contribution in IDR.
    """
    defaults = _get_insurance_defaults(employment_type)

    if insurance_config:
        bpjs_kes = float(insurance_config.get("bpjs_kesehatan_employer", defaults["bpjs_kes_employer"]))
    else:
        bpjs_kes = defaults["bpjs_kes_employer"]

    # JKK + JKM + JHT employer + JP employer only for full_time/part_time
    if employment_type in ("full_time", "part_time"):
        employer_jht = 0.037
        employer_jp = 0.02
        jkk = 0.0024
        jkm = 0.003
    else:
        employer_jht = 0.0
        employer_jp = 0.0
        jkk = 0.0
        jkm = 0.0

    total_rate = bpjs_kes + employer_jht + employer_jp + jkk + jkm
    return round(gross * total_rate, 2)


def _get_insurance_defaults(employment_type: str) -> dict[str, float]:
    """Return default BPJS rates keyed by component for an employment type."""
    if employment_type in ("full_time", "part_time"):
        return {
            "bpjs_kes_employee": 0.01,
            "bpjs_kes_employer": 0.04,
            "jht_employee": 0.02,
            "jp_employee": 0.01,
        }
    if employment_type in ("honorer", "honorary"):
        return {
            "bpjs_kes_employee": 0.01,
            "bpjs_kes_employer": 0.04,
            "jht_employee": 0.0,
            "jp_employee": 0.0,
        }
    # internship, freelance — no mandatory insurance
    return {
        "bpjs_kes_employee": 0.0,
        "bpjs_kes_employer": 0.0,
        "jht_employee": 0.0,
        "jp_employee": 0.0,
    }
