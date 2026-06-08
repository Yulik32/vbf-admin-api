# create_user_fixed.py
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

def create_user():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Добавляем колонку если нет
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS page_permissions TEXT")
        conn.commit()
    except:
        pass
    
    email = "admin@vbf.ru"
    password = "admin123"
    hashed = pwd_context.hash(password)
    
    # Удаляем старого
    cursor.execute("DELETE FROM users WHERE email = %s", (email,))
    
    # Создаем нового с ролью super_admin
    cursor.execute("""
        INSERT INTO users (email, hashed_password, full_name, role, is_active)
        VALUES (%s, %s, %s, %s, %s)
    """, (email, hashed, 'Administrator', 'super_admin', True))
    
    conn.commit()
    
    print("=" * 50)
    print("✅ ПОЛЬЗОВАТЕЛЬ СОЗДАН")
    print("=" * 50)
    print(f"   Email: {email}")
    print(f"   Пароль: {password}")
    print(f"   Роль: super_admin")
    print("=" * 50)
    
    # Проверяем
    cursor.execute("SELECT id, email, role FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    if user:
        print(f"   ID: {user[0]}, Role: {user[2]}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    create_user()