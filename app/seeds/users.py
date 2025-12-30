import asyncio
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.auth.jwt import auth_service


USERS = [
    # 🔑 ADMIN DS
    {
        "username": "admin.ds",
        "password": "admin123",
        "full_name": "Admin Direction Système",
        "role": UserRole.ADMIN,
        "department": "DS",
    },

    # 🎛️ CONTROLLERS DS03
    {
        "username": "controller.ds03.1",
        "password": "controller123",
        "full_name": "Controller DS03 A",
        "role": UserRole.CONTROLLER,
        "department": "DS03",
    },
    {
        "username": "controller.ds03.2",
        "password": "controller123",
        "full_name": "Controller DS03 B",
        "role": UserRole.CONTROLLER,
        "department": "DS03",
    },

    # 🎛️ CONTROLLERS DS07
    {
        "username": "controller.ds07.1",
        "password": "controller123",
        "full_name": "Controller DS07 A",
        "role": UserRole.CONTROLLER,
        "department": "DS07",
    },
    {
        "username": "controller.ds07.2",
        "password": "controller123",
        "full_name": "Controller DS07 B",
        "role": UserRole.CONTROLLER,
        "department": "DS07",
    },
]


async def seed_users() -> None:
    async with AsyncSessionLocal() as session:
        for data in USERS:
            result = await session.execute(
                select(User).where(User.username == data["username"])
            )
            exists = result.scalar_one_or_none()

            if exists:
                continue  # idempotent

            user = User(
                username=data["username"],
                hashed_password=auth_service.hash_password(data["password"]),
                full_name=data["full_name"],
                role=data["role"],
                department=data["department"],
                is_active=True,
            )
            session.add(user)

        await session.commit()

    print("✅ Users seeded successfully")


if __name__ == "__main__":
    asyncio.run(seed_users())
