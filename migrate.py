import sqlite3
import psycopg2

# Подключение к SQLite
sqlite_conn = sqlite3.connect('admin.db')
sqlite_cursor = sqlite_conn.cursor()

# Подключение к PostgreSQL
pg_conn = psycopg2.connect(
    host="dpg-d8eum719rddc73c3f890-a.oregon-postgres.render.com",
    port=5432,
    user="vbf_db_pky7_user",
    password="TgAb3GTbcMgMg8mo6dPpGtVlI7KCLT4Y",
    database="vbf_db_pky7"
)
pg_cursor = pg_conn.cursor()

print("=" * 50)
print("Перенос данных сервиса (service_phones)")
print("=" * 50)

# Проверяем, какие колонки есть в таблице service_phone в SQLite
sqlite_cursor.execute("PRAGMA table_info(service_phone)")
columns = [col[1] for col in sqlite_cursor.fetchall()]
print(f"Колонки service_phone в SQLite: {columns}")

# Если нет, пробуем другое название
if not columns:
    sqlite_cursor.execute("PRAGMA table_info(service_phones)")
    columns = [col[1] for col in sqlite_cursor.fetchall()]
    print(f"Колонки service_phones в SQLite: {columns}")

# Создаём таблицу в PostgreSQL, если её нет
pg_cursor.execute("""
    CREATE TABLE IF NOT EXISTS service_phone (
        id SERIAL PRIMARY KEY,
        section_key VARCHAR(100),
        title_ru TEXT,
        title_en TEXT,
        phone VARCHAR(50),
        "order" INTEGER DEFAULT 0,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_by INTEGER
    )
""")
print("✅ Таблица service_phone создана/проверена")

if columns:
    # Получаем данные из SQLite
    select_cols = ', '.join([f'"{col}"' if col == 'order' else col for col in columns])
    try:
        sqlite_cursor.execute(f"SELECT {select_cols} FROM service_phone")
    except:
        sqlite_cursor.execute(f"SELECT {select_cols} FROM service_phones")
    
    rows = sqlite_cursor.fetchall()
    print(f"Найдено {len(rows)} записей в SQLite")
    
    for row in rows:
        values = []
        for i, col in enumerate(columns):
            val = row[i]
            if col == 'is_active':
                val = val == 1  # Преобразуем в boolean
            values.append(val)
        
        insert_cols = ', '.join([f'"{col}"' if col == 'order' else col for col in columns])
        placeholders = ','.join(['%s'] * len(columns))
        
        try:
            pg_cursor.execute(f"""
                INSERT INTO service_phone ({insert_cols})
                VALUES ({placeholders})
                ON CONFLICT (id) DO NOTHING
            """, values)
        except Exception as e:
            print(f"Ошибка при вставке: {e}")
    
    pg_conn.commit()
    print(f"✅ Перенесено {len(rows)} записей в service_phone")
else:
    print("⚠️ Таблица service_phone не найдена в SQLite (нет данных для переноса)")

# Проверяем результат
pg_cursor.execute("SELECT COUNT(*) FROM service_phone")
count = pg_cursor.fetchone()[0]
print(f"Всего записей в PostgreSQL service_phone: {count}")

# Показываем первые 5 записей для проверки
pg_cursor.execute("SELECT id, section_key, title_ru, phone FROM service_phone LIMIT 5")
rows = pg_cursor.fetchall()
print("\nПервые 5 записей в PostgreSQL:")
for row in rows:
    print(f"  id={row[0]}, section_key={row[1]}, title={row[2]}, phone={row[3]}")

sqlite_conn.close()
pg_conn.close()
print("🎉 Готово!")