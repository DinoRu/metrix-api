import pytest
from httpx import AsyncClient
from datetime import datetime
from app.models.meter import Meter
from app.models.reading import Reading
from app.models.user import User


@pytest.fixture
async def test_reading(db_session, test_meter: Meter, test_user: User) -> Reading:
	"""Create a test reading"""
	reading = Reading(
		meter_id=test_meter.id,
		user_id=test_user.id,
		reading_value=12345.678,
		reading_date=datetime.utcnow(),
		latitude=48.8566,
		longitude=2.3522,
		notes="Test reading"
	)
	db_session.add(reading)
	await db_session.commit()
	await db_session.refresh(reading)
	return reading


@pytest.mark.asyncio
async def test_create_reading(client: AsyncClient, test_meter: Meter, auth_token: str):
	"""Test creating a reading"""
	response = await client.post(
		"/api/v1/readings",
		headers={"Authorization": f"Bearer {auth_token}"},
		json={
			"meter_id": str(test_meter.id),
			"reading_value": 54321.123,
			"reading_date": datetime.utcnow().isoformat(),
			"latitude": 48.8566,
			"longitude": 2.3522,
			"notes": "New test reading",
			"client_id": "test-client-id-001"
		}
	)
	assert response.status_code == 201
	data = response.json()
	assert data["reading_value"] == 54321.123
	assert data["meter_id"] == str(test_meter.id)


@pytest.mark.asyncio
async def test_create_duplicate_client_id(client: AsyncClient, test_meter: Meter, auth_token: str):
	"""Test creating reading with duplicate client_id"""
	# First reading
	response = await client.post(
		"/api/v1/readings",
		headers={"Authorization": f"Bearer {auth_token}"},
		json={
			"meter_id": str(test_meter.id),
			"reading_value": 11111,
			"reading_date": datetime.utcnow().isoformat(),
			"client_id": "duplicate-id"
		}
	)
	assert response.status_code == 201

	# Duplicate attempt
	response = await client.post(
		"/api/v1/readings",
		headers={"Authorization": f"Bearer {auth_token}"},
		json={
			"meter_id": str(test_meter.id),
			"reading_value": 22222,
			"reading_date": datetime.utcnow().isoformat(),
			"client_id": "duplicate-id"
		}
	)
	assert response.status_code == 409
	assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_readings(client: AsyncClient, test_reading: Reading, auth_token: str):
	"""Test listing readings"""
	response = await client.get(
		"/api/v1/readings",
		headers={"Authorization": f"Bearer {auth_token}"}
	)
	assert response.status_code == 200
	data = response.json()
	assert data["total"] >= 1
	assert len(data["data"]) >= 1


@pytest.mark.asyncio
async def test_sync_readings(client: AsyncClient, test_meter: Meter, auth_token: str):
	"""Test syncing multiple readings"""
	readings_data = [
		{
			"meter_id": str(test_meter.id),
			"reading_value": 100.0,
			"reading_date": datetime.utcnow().isoformat(),
			"client_id": f"sync-{i}"
		}
		for i in range(3)
	]

	response = await client.post(
		"/api/v1/readings/sync",
		headers={"Authorization": f"Bearer {auth_token}"},
		json={
			"readings": readings_data,
			"device_id": "test-device-001"
		}
	)
	assert response.status_code == 200
	data = response.json()
	assert data["synced"] == 3
	assert data["failed"] == 0