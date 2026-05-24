from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_MONTH_NAMES_ID = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]


def _fmt_idr(amount: float) -> str:
    return "Rp {:,.0f}".format(amount).replace(",", ".")


def render_payslip_pdf(
    *,
    school_name: str,
    employee_name: str,
    employee_number: str | None,
    position: str | None,
    department: str | None,
    employment_type: str,
    period_month: int,
    period_year: int,
    base_salary: float,
    allowances: list[dict[str, Any]],
    gross_salary: float,
    tax_amount: float,
    bpjs_employee: float,
    one_time_adjustments: list[dict[str, Any]],
    net_salary: float,
) -> bytes:
    period_label = f"{_MONTH_NAMES_ID[period_month - 1]} {period_year}"

    allowances_ctx = [
        {**a, "amount_fmt": _fmt_idr(float(a.get("amount", 0)))}
        for a in allowances
    ]
    one_time_additions = [
        {**a, "amount_fmt": _fmt_idr(float(a.get("amount", 0)))}
        for a in one_time_adjustments
        if a.get("type") == "addition"
    ]
    one_time_deductions = [
        {**a, "amount_fmt": _fmt_idr(float(a.get("amount", 0)))}
        for a in one_time_adjustments
        if a.get("type") == "deduction"
    ]

    env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)), autoescape=True)
    template = env.get_template("payslip.html")
    html_str = template.render(
        school_name=school_name,
        employee_name=employee_name,
        employee_number=employee_number,
        position=position,
        department=department,
        employment_type=employment_type,
        period_label=period_label,
        base_salary_fmt=_fmt_idr(base_salary),
        allowances=allowances_ctx,
        gross_salary_fmt=_fmt_idr(gross_salary),
        tax_amount_fmt=_fmt_idr(tax_amount),
        bpjs_employee_fmt=_fmt_idr(bpjs_employee),
        one_time_additions=one_time_additions,
        one_time_deductions=one_time_deductions,
        net_salary_fmt=_fmt_idr(net_salary),
        printed_at=datetime.now().strftime("%d/%m/%Y %H:%M"),
    )

    from weasyprint import HTML  # noqa: PLC0415 — deferred to avoid startup cost

    return HTML(string=html_str).write_pdf()
