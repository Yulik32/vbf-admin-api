from database import SessionLocal, Base, engine
from auth import get_password_hash
import models

def reset_database():
    print("🔄 Удаляем все таблицы...")
    Base.metadata.drop_all(bind=engine)
    
    print("🔄 Создаём таблицы заново...")
    Base.metadata.create_all(bind=engine)
    
    print("✅ База данных пересоздана")
    
    db = SessionLocal()
    
    try:
        # Создаём админа
        admin = models.User(
            email="admin@example.com",
            hashed_password=get_password_hash("admin123"),
            full_name="Admin User",
            role="admin",
            is_active=True
        )
        db.add(admin)
        db.commit()
        
        print("✅ Админ создан: admin@example.com / admin123")
        
        # Проверяем
        users = db.query(models.User).all()
        print("\n📋 Пользователи в БД:")
        for user in users:
            print(f"   - {user.email} (роль: {user.role})")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_database()