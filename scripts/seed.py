from app.database import SessionLocal
from app.seeds.users import seed_users


def run():
    db = SessionLocal()
    try:
        seed_users(db)
        print("✅ Users seeded successfully")
    finally:
        db.close()


if __name__ == "__main__":
    run()
