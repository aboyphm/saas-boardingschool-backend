from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.certificates.models import Certificate
from app.domains.certificates.schemas import CertificateCreate, CertificateUpdate
from app.shared.base_repository import BaseRepository
from app.shared.enums import CertificateType


class CertificateRepository(
    BaseRepository[Certificate, CertificateCreate, CertificateUpdate]
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Certificate, session)

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        student_id: uuid.UUID | None = None,
        certificate_type: CertificateType | None = None,
        include_revoked: bool = False,
    ) -> list[Certificate]:
        stmt = (
            select(Certificate)
            .where(Certificate.tenant_id == tenant_id)
            .order_by(Certificate.issued_at.desc())
        )
        if student_id:
            stmt = stmt.where(Certificate.student_id == student_id)
        if certificate_type:
            stmt = stmt.where(Certificate.certificate_type == certificate_type)
        if not include_revoked:
            stmt = stmt.where(Certificate.is_revoked.is_(False))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_tenant(
        self, cert_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Certificate | None:
        stmt = select(Certificate).where(
            Certificate.id == cert_id,
            Certificate.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_number(self, certificate_number: str) -> Certificate | None:
        """Public lookup — no tenant scope (for verification)."""
        stmt = select(Certificate).where(
            Certificate.certificate_number == certificate_number,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
