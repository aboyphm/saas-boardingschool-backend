from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from app.core.exceptions import ConflictError, NotFoundError
from app.domains.certificates.models import Certificate
from app.domains.certificates.repository import CertificateRepository
from app.domains.certificates.schemas import (
    CertificateCreate, CertificateResponse, CertificateUpdate, RevokeRequest,
)
from app.shared.enums import CertificateType


def _generate_cert_number(tenant_id: uuid.UUID, cert_type: CertificateType) -> str:
    """Generate a unique certificate number: CERT-{TYPE_PREFIX}-{TENANT_SHORT}-{TIMESTAMP}."""
    prefix_map = {
        CertificateType.GRADUATION: "GRD",
        CertificateType.HAFALAN_COMPLETION: "HAF",
        CertificateType.ACADEMIC_ACHIEVEMENT: "ACH",
        CertificateType.COURSE_COMPLETION: "CRS",
        CertificateType.OTHER: "OTH",
    }
    prefix = prefix_map.get(cert_type, "OTH")
    tenant_short = str(tenant_id).replace("-", "")[:6].upper()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"CERT-{prefix}-{tenant_short}-{timestamp}"


class CertificateService:
    def __init__(self, repo: CertificateRepository) -> None:
        self.repo = repo

    async def list_certificates(
        self,
        tenant_id: uuid.UUID,
        student_id: uuid.UUID | None = None,
        certificate_type: CertificateType | None = None,
        include_revoked: bool = False,
    ) -> list[Certificate]:
        return await self.repo.list_by_tenant(
            tenant_id, student_id, certificate_type, include_revoked,
        )

    async def get_or_404(
        self, cert_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Certificate:
        cert = await self.repo.get_by_tenant(cert_id, tenant_id)
        if cert is None:
            raise NotFoundError("Certificate not found.")
        return cert

    async def issue_certificate(
        self,
        data: CertificateCreate,
        tenant_id: uuid.UUID,
        issued_by: uuid.UUID,
    ) -> Certificate:
        cert_number = _generate_cert_number(tenant_id, data.certificate_type)
        cert = Certificate(
            tenant_id=tenant_id,
            student_id=data.student_id,
            issued_by=issued_by,
            certificate_number=cert_number,
            certificate_type=data.certificate_type,
            title=data.title,
            description=data.description,
            issued_at=data.issued_at,
            is_revoked=False,
        )
        self.repo.session.add(cert)
        await self.repo.session.flush()
        await self.repo.session.refresh(cert)
        return cert

    async def update_certificate(
        self,
        cert_id: uuid.UUID,
        data: CertificateUpdate,
        tenant_id: uuid.UUID,
    ) -> Certificate:
        cert = await self.get_or_404(cert_id, tenant_id)
        if cert.is_revoked:
            raise ConflictError("Cannot update a revoked certificate.")
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(cert, field, value)
        await self.repo.session.flush()
        await self.repo.session.refresh(cert)
        return cert

    async def revoke_certificate(
        self,
        cert_id: uuid.UUID,
        data: RevokeRequest,
        revoked_by: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Certificate:
        cert = await self.get_or_404(cert_id, tenant_id)
        if cert.is_revoked:
            raise ConflictError("Certificate is already revoked.")
        cert.is_revoked = True
        cert.revoked_at = datetime.now(timezone.utc)
        cert.revoked_by = revoked_by
        cert.revocation_reason = data.revocation_reason
        await self.repo.session.flush()
        await self.repo.session.refresh(cert)
        return cert

    async def verify_certificate(self, certificate_number: str) -> Certificate | None:
        """Public lookup — no auth required."""
        return await self.repo.get_by_number(certificate_number)
