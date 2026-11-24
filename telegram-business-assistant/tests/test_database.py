import pytest

from src.database import Database


@pytest.mark.asyncio
async def test_lead_is_persisted_and_returned(tmp_path):
    database = Database(str(tmp_path / "leads.sqlite3"))
    await database.initialize()

    lead_id = await database.add_lead(
        telegram_user_id=12345,
        username="demo_user",
        customer_name="Demo Customer",
        contact="demo@example.com",
        service="Приём заявок",
        details="Нужен бот для первичного сбора заявок.",
    )
    leads = await database.get_recent_leads()

    assert lead_id == 1
    assert len(leads) == 1
    assert leads[0]["telegram_user_id"] == 12345
    assert leads[0]["contact"] == "demo@example.com"
    assert leads[0]["service"] == "Приём заявок"


@pytest.mark.asyncio
async def test_recent_leads_are_limited_and_newest_first(tmp_path):
    database = Database(str(tmp_path / "leads.sqlite3"))
    await database.initialize()

    for index in range(4):
        await database.add_lead(
            telegram_user_id=1000 + index,
            username=None,
            customer_name=f"Customer {index}",
            contact=f"customer{index}@example.com",
            service="Приём заявок",
            details=f"Request number {index} with enough details.",
        )

    leads = await database.get_recent_leads(limit=2)

    assert [lead["telegram_user_id"] for lead in leads] == [1003, 1002]


@pytest.mark.asyncio
async def test_recent_leads_returns_empty_when_database_has_no_leads(tmp_path):
    database = Database(str(tmp_path / "leads.sqlite3"))
    await database.initialize()

    assert await database.get_recent_leads() == []


@pytest.mark.asyncio
async def test_recent_leads_limit_is_clamped_to_safe_range(tmp_path):
    database = Database(str(tmp_path / "leads.sqlite3"))
    await database.initialize()

    for index in range(51):
        await database.add_lead(
            telegram_user_id=2000 + index,
            username=None,
            customer_name=f"Customer {index}",
            contact=f"customer{index}@example.com",
            service="Приём заявок",
            details="A sufficiently detailed test request.",
        )

    assert len(await database.get_recent_leads(limit=0)) == 1
    assert len(await database.get_recent_leads(limit=-10)) == 1
    assert len(await database.get_recent_leads(limit=100)) == 50
