# =====================================
# api/tests/test_auth.py
# =====================================
import pytest
from httpx import AsyncClient
from app.models.user import User

@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Test user registration"""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "securepass123",
            "full_name": "New User",
            "role": "controller"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["role"] == "controller"
    assert "id" in data

@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user: User):
    """Test registration with duplicate email"""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": test_user.email,
            "password": "password123",
            "role": "controller"
        }
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: User):
    """Test successful login"""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "testpass123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == test_user.email

@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """Test login with invalid credentials"""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "wrong@example.com",
            "password": "wrongpass"
        }
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]

@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, test_user: User, auth_token: str):
    """Test getting current user info"""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["id"] == str(test_user.id)

@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    """Test accessing protected endpoint without token"""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 403  # No credentials provided

@pytest.mark.asyncio
async def test_invalid_token(client: AsyncClient):
    """Test accessing protected endpoint with invalid token"""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401