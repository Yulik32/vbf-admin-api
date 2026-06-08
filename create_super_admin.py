# update_to_super_admin.py
import psycopg2
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'dpg-d8eum719rddc73c3f890-a.oregon-postgres.render.com'),
    'port': os.getenv('DB_PORT', 5432),
    'database': os.getenv('DB_NAME', 'vbf_db_pky7'),
    'user': os.getenv('DB_USER', 'vbf_db_pky7_user'),
    'password': os.getenv('DB_PASSWORD', 'TgAb3GTbcMgMg8mo6dPpGtVlI7KCLT4Y')
}

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def update_to_super_admin():
    print("=" * 50)
    print("ОБНОВЛЕНИЕ ДО SUPER_ADMIN")
    print("=" * 50)
    print(f"Хост: {DB_CONFIG['host']}")
    print(f"База: {DB_CONFIG['database']}")
    print()
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("✅ Подключение к PostgreSQL установлено")
        
        # Сначала добавляем колонку page_permissions если её нет
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS page_permissions TEXT")
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            conn.commit()
            print("✅ Добавлены недостающие колонки")
        except Exception as e:
            print(f"⚠️ Колонки уже есть или ошибка: {e}")
        
        # Проверяем существующих пользователей
        cursor.execute("SELECT id, email, role FROM users")
        users = cursor.fetchall()
        print("\n📋 Существующие пользователи:")
        for user in users:
            print(f"   ID: {user[0]}, Email: {user[1]}, Role: {user[2]}")
        
        # Обновляем пользователя с id=1 до super_admin
        email = "superadmin@vbf.ru"
        password = "superadmin123"
        hashed_password = pwd_context.hash(password)
        
        # Проверяем, существует ли пользователь с id=1
        cursor.execute("SELECT id, email, role FROM users WHERE id = 1")
        user = cursor.fetchone()
        
        if user:
            print(f"\n📋 Найден пользователь с id=1:")
            print(f"   Email: {user[1]}")
            print(f"   Текущая роль: {user[2]}")
            
            # Обновляем существующего пользователя
            cursor.execute("""
                UPDATE users 
                SET role = 'super_admin', 
                    email = %s,
                    hashed_password = %s,
                    full_name = 'Super Administrator',
                    is_active = true,
                    page_permissions = NULL
                WHERE id = 1
            """, (email, hashed_password))
            print(f"\n✅ Пользователь с id=1 обновлен до super_admin")
        else:
            print("\n⚠️ Пользователь с id=1 не найден")
            # Создаем нового с id=1
            cursor.execute("""
                INSERT INTO users (id, email, hashed_password, full_name, role, is_active, page_permissions)
                VALUES (1, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET 
                    role = 'super_admin',
                    email = EXCLUDED.email,
                    hashed_password = EXCLUDED.hashed_password,
                    full_name = EXCLUDED.full_name,
                    is_active = true,
                    page_permissions = NULL
            """, (email, hashed_password, 'Super Administrator', 'super_admin', True, None))
            print(f"\n✅ Super_admin создан с id=1")
        
        conn.commit()
        
        # Проверяем результат
        cursor.execute("SELECT id, email, role FROM users WHERE id = 1")
        user = cursor.fetchone()
        print(f"\n📋 Результат:")
        print(f"   ID: {user[0]}")
        print(f"   Email: {user[1]}")
        print(f"   Role: {user[2]}")
        
        cursor.close()
        conn.close()
        
        print(f"\n🎉 Готово!")
        print(f"   Email: {email}")
        print(f"   Пароль: {password}")
        print(f"\n⚠️ Используйте эти данные для входа в админку!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    update_to_super_admin()