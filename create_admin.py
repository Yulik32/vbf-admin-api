# create_admin.py
from database import SessionLocal
from auth import get_password_hash
import models

db = SessionLocal()

# Проверяем, есть ли уже админ
admin = db.query(models.User).filter(models.User.email == "admin@example.com").first()

if not admin:
    admin_user = models.User(
        email="admin@example.com",
        hashed_password=get_password_hash("admin123"),
        full_name="Admin",
        role="admin",
        is_active=True
    )
    db.add(admin_user)
    db.commit()
    print("✅ Админ создан: admin@example.com / admin123")
else:
    print("⚠️ Админ уже существует")

db.close()