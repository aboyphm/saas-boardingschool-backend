from __future__ import annotations

import asyncio
from datetime import date, timedelta

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    name="app.infrastructure.queue.tasks.hr_tasks.check_contract_expiry",
)
def check_contract_expiry() -> dict:
    """
    Scheduled task: warn when employee contracts are expiring within 30 days.
    Runs daily at 09:00 WIB.
    """
    from app.core.database import get_db_session
    from app.domains.hr.models import EmployeeContract
    from app.shared.enums import ContractStatus
    from sqlalchemy import and_, select

    async def _run() -> int:
        today = date.today()
        alert_cutoff = today + timedelta(days=30)

        async with get_db_session() as session:
            stmt = select(EmployeeContract).where(
                and_(
                    EmployeeContract.status == ContractStatus.ACTIVE,
                    EmployeeContract.end_date.isnot(None),
                    EmployeeContract.end_date >= today,
                    EmployeeContract.end_date <= alert_cutoff,
                )
            )
            result = await session.execute(stmt)
            contracts = result.scalars().all()

            for contract in contracts:
                days_left = (contract.end_date - today).days
                logger.warning(
                    "Contract expiring in %d day(s): contract_id=%s tenant_id=%s user_id=%s end_date=%s",
                    days_left,
                    str(contract.id),
                    str(contract.tenant_id),
                    str(contract.user_id),
                    str(contract.end_date),
                )

            return len(contracts)

    expiring_count = asyncio.run(_run())
    logger.info(
        "Contract expiry check complete — %d contract(s) expiring within 30 days",
        expiring_count,
    )
    return {"status": "completed", "expiring_contracts": expiring_count}
