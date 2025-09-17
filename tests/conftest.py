import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.main import app
from app.database import Base, get_session
from app.config import settings
from app.auth.jwt import auth_service
from app.models.user import User, UserRole

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/meter_reading_test"


@pytest.fixture(scope="session")
def event_loop():
	"""Create an instance of the default event loop for the test session."""
	loop = asyncio.get_event_loop_policy().new_event_loop()
	yield loop
	loop.close()


@pytest.fixture(scope="session")
async def engine():
	"""Create test database engine"""
	engine = create_async_engine(TEST_DATABASE_URL, echo=False)

	async with engine.begin() as conn:
		await conn.run_sync(Base.metadata.create_all)

	yield engine

	async with engine.begin() as conn:
		await conn.run_sync(Base.metadata.drop_all)

	await engine.dispose()


@pytest.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
	"""Create a test database session"""
	async_session = async_sessionmaker(
		engine, class_=AsyncSession, expire_on_commit=False
	)

	async with async_session() as session:
		yield session
		await session.rollback()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
	"""Create a test client"""

	def override_get_session():
		return db_session

	app.dependency_overrides[get_session] = override_get_session

	async with AsyncClient(app=app, base_url="http://test") as client:
		yield client

	app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
	"""Create a test user"""
	user = User(
		email="test@example.com",
		hashed_password=auth_service.hash_password("testpass123"),
		full_name="Test User",
		role=UserRole.CONTROLLER,
		is_active=True
	)
	db_session.add(user)
	await db_session.commit()
	await db_session.refresh(user)
	return user


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
	"""Create a test admin user"""
	user = User(
		email="admin@example.com",
		hashed_password=auth_service.hash_password("adminpass123"),
		full_name="Admin User",
		role=UserRole.ADMIN,
		is_active=True
	)
	db_session.add(user)
	await db_session.commit()
	await db_session.refresh(user)
	return user


@pytest.fixture
def auth_token(test_user: User) -> str:
	"""Generate auth token for test user"""
	return auth_service.create_access_token({"sub": str(test_user.id), "role": test_user.role})


@pytest.fixture
def admin_token(admin_user: User) -> str:
	"""Generate auth token for admin user"""
	return auth_service.create_access_token({"sub": str(admin_user.id), "role": admin_user.role})