from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import Field, field_validator

from app.shared.base_schema import BaseSchema
from app.shared.enums import ContractStatus, EmploymentType, PayrollRunStatus


# ─── Allowance sub-schema ─────────────────────────────────────────────────────

class AllowanceItem(BaseSchema):
    name: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., ge=0)
    taxable: bool = True


# ─── One-time adjustment sub-schema ──────────────────────────────────────────

class OneTimeAdjustment(BaseSchema):
    description: str = Field(..., min_length=1, max_length=255)
    amount: float = Field(..., ge=0)
    type: str = Field(..., pattern="^(addition|deduction)$")


# ─── Employee Contract schemas ────────────────────────────────────────────────

class ContractCreate(BaseSchema):
    user_id: uuid.UUID
    employee_number: str | None = None
    employment_type: EmploymentType
    position: str | None = None
    department: str | None = None
    start_date: date
    end_date: date | None = None
    base_salary: float = Field(default=0.0, ge=0)
    status: ContractStatus = ContractStatus.ACTIVE
    tax_config: dict[str, Any] | None = None
    insurance_config: dict[str, Any] | None = None
    allowances: list[AllowanceItem] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("end_date")
    @classmethod
    def end_date_after_start(cls, v: date | None, info: Any) -> date | None:
        if v is not None:
            start = info.data.get("start_date")
            if start and v <= start:
                raise ValueError("end_date must be after start_date.")
        return v

    @field_validator("base_salary")
    @classmethod
    def validate_salary(cls, v: float, info: Any) -> float:
        emp_type = info.data.get("employment_type")
        if emp_type != EmploymentType.INTERNSHIP and v < 0:
            raise ValueError("base_salary must be >= 0.")
        return v


class ContractUpdate(BaseSchema):
    employee_number: str | None = None
    employment_type: EmploymentType | None = None
    position: str | None = None
    department: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    base_salary: float | None = Field(default=None, ge=0)
    status: ContractStatus | None = None
    tax_config: dict[str, Any] | None = None
    insurance_config: dict[str, Any] | None = None
    allowances: list[AllowanceItem] | None = None
    notes: str | None = None


class ContractResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    user_id: uuid.UUID
    user_full_name: str | None = None
    employee_number: str | None
    employment_type: EmploymentType
    position: str | None
    department: str | None
    start_date: date
    end_date: date | None
    base_salary: float
    status: ContractStatus
    tax_config: dict[str, Any] | None
    insurance_config: dict[str, Any] | None
    allowances: list[dict[str, Any]]
    notes: str | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ─── Payroll Run schemas ──────────────────────────────────────────────────────

class PayrollRunCreate(BaseSchema):
    period_month: int = Field(..., ge=1, le=12)
    period_year: int = Field(..., ge=2000, le=2100)
    # Keyed by user_id string; each value is a list of one-time adjustments for that employee
    one_time_adjustments: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    notes: str | None = None


class PayrollRunUpdate(BaseSchema):
    notes: str | None = None
    one_time_adjustments: dict[str, list[dict[str, Any]]] | None = None


class PayrollRecordResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    teacher_id: uuid.UUID
    employee_name: str | None = None
    contract_id: uuid.UUID | None
    payroll_run_id: uuid.UUID | None
    period_month: int
    period_year: int
    base_salary: float
    gross_salary: float | None
    allowances_total: float
    tax_amount: float | None
    bpjs_employee: float | None
    bpjs_employer: float | None
    other_deductions: float
    one_time_adjustments: list[dict[str, Any]]
    net_salary: float
    status: str
    created_at: datetime


class PayrollRunResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    period_month: int
    period_year: int
    status: PayrollRunStatus
    total_gross: float
    total_deductions: float
    total_net: float
    run_by: uuid.UUID
    approved_by: uuid.UUID | None
    run_at: datetime
    approved_at: datetime | None
    paid_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    records: list[PayrollRecordResponse] = Field(default_factory=list)


# ─── Payroll Preview schemas ──────────────────────────────────────────────────

class EmployeePreviewRow(BaseSchema):
    user_id: uuid.UUID
    full_name: str
    employment_type: str
    base_salary: float
    allowances_total: float
    gross_salary: float
    tax_amount: float
    bpjs_employee: float
    bpjs_employer: float
    other_deductions: float
    net_salary: float


class PayrollPreviewRequest(BaseSchema):
    period_month: int = Field(..., ge=1, le=12)
    period_year: int = Field(..., ge=2000, le=2100)
    # Per-employee one-time adjustments keyed by user_id string
    one_time_adjustments: dict[str, list[OneTimeAdjustment]] = Field(default_factory=dict)


class PayrollPreviewResponse(BaseSchema):
    period_month: int
    period_year: int
    employees: list[EmployeePreviewRow]
    total_gross: float
    total_deductions: float
    total_net: float


# ─── Missing-contract employee entry (422 payload) ────────────────────────────

class MissingContractEntry(BaseSchema):
    user_id: uuid.UUID
    full_name: str
    role: str
