# =====================================
import pytest
from httpx import AsyncClient
from app.models.meter import Meter
from app.models.user import User


@pytest.fixture
async def test_meter(db_session) -> Meter:
	"""Create a test meter"""
	meter = Meter(
		meter_number="TEST-001",
		type="electricity",
		location_address="123 Test St",
		latitude=48.8566,
		longitude=2.3522,
		client_name="Test Client",
		status="active"
	)
	db_session.add(meter)
	await db_session.commit()
	await db_session.refresh(meter)
	return meter


@pytest.mark.asyncio
async def test_list_meters(client: AsyncClient, test_meter: Meter, auth_token: str):
	"""Test listing meters"""
	response = await client.get(
		"/api/v1/meters",
		headers={"Authorization": f"Bearer {auth_token}"}
	)
	assert response.status_code == 200
	data = response.json()
	assert data["total"] >= 1
	assert len(data["data"]) >= 1
	assert any(m["meter_number"] == test_meter.meter_number for m in data["data"])


@pytest.mark.asyncio
async def test_get_meter(client: AsyncClient, test_meter: Meter, auth_token: str):
	"""Test getting a specific meter"""
	response = await client.get(
		f"/api/v1/meters/{test_meter.id}",
		headers={"Authorization": f"Bearer {auth_token}"}
	)
	assert response.status_code == 200
	data = response.json()
	assert data["meter_number"] == test_meter.meter_number
	assert data["type"] == test_meter.type


@pytest.mark.asyncio
async def test_create_meter_as_admin(client: AsyncClient, admin_token: str):
	"""Test creating a meter as admin"""
	response = await client.post(
		"/api/v1/meters",
		headers={"Authorization": f"Bearer {admin_token}"},
		json={
			"meter_number": "NEW-001",
			"type": "water",
			"location_address": "456 New St",
			"client_name": "New Client"
		}
	)
	assert response.status_code == 201
	data = response.json()
	assert data["meter_number"] == "NEW-001"
	assert data["type"] == "water"


@pytest.mark.asyncio
async def test_create_meter_as_controller_forbidden(client: AsyncClient, auth_token: str):
	"""Test that controllers cannot create meters"""
	response = await client.post(
		"/api/v1/meters",
		headers={"Authorization": f"Bearer {auth_token}"},
		json={
			"meter_number": "FORBIDDEN-001",
			"type": "gas"
		}
	)
	assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_meter(client: AsyncClient, test_meter: Meter, admin_token: str):
	"""Test updating a meter"""
	response = await client.patch(
		f"/api/v1/meters/{test_meter.id}",
		headers={"Authorization": f"Bearer {admin_token}"},
		json={
			"status": "inactive",
			"client_name": "Updated Client"
		}
	)
	assert response.status_code == 200
	data = response.json()
	assert data["status"] == "inactive"
	assert data["client_name"] == "Updated Client"


@pytest.mark.asyncio
async def test_delete_meter(client: AsyncClient, test_meter: Meter, admin_token: str):
	"""Test deleting a meter"""
	response = await client.delete(
		f"/api/v1/meters/{test_meter.id}",
		headers={"Authorization": f"Bearer {admin_token}"}
	)
	assert response.status_code == 204

	# Verify deletion
	response = await client.get(
		f"/api/v1/meters/{test_meter.id}",
		headers={"Authorization": f"Bearer {admin_token}"}
	)
	assert response.status_code == 404