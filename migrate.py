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
print("Перенос данных каталога (catalog_card)")
print("=" * 50)

# Проверяем, какие колонки есть в таблице catalog_card в SQLite
sqlite_cursor.execute("PRAGMA table_info(catalog_card)")
columns = [col[1] for col in sqlite_cursor.fetchall()]
print(f"Колонки catalog_card в SQLite: {columns}")

# Если нет, пробуем другое название
if not columns:
    sqlite_cursor.execute("PRAGMA table_info(catalog_cards)")
    columns = [col[1] for col in sqlite_cursor.fetchall()]
    print(f"Колонки catalog_cards в SQLite: {columns}")

if not columns:
    print("❌ Таблица catalog_card не найдена в SQLite!")
    print("Доступные таблицы:")
    sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = sqlite_cursor.fetchall()
    for t in tables:
        print(f"  - {t[0]}")
    exit()

# Создаём таблицу в PostgreSQL, если её нет
pg_cursor.execute("""
    CREATE TABLE IF NOT EXISTS catalog_card (
        id SERIAL PRIMARY KEY,
        title_ru TEXT,
        title_en TEXT,
        description_ru TEXT,
        description_en TEXT,
        file_url TEXT,
        icon_type VARCHAR(20),
        "order" INTEGER DEFAULT 0,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_by INTEGER
    )
""")
print("✅ Таблица catalog_card создана/проверена")

# Получаем данные из SQLite
select_cols = ', '.join([f'"{col}"' if col == 'order' else col for col in columns])
try:
    sqlite_cursor.execute(f"SELECT {select_cols} FROM catalog_card")
except:
    sqlite_cursor.execute(f"SELECT {select_cols} FROM catalog_cards")

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
            INSERT INTO catalog_card ({insert_cols})
            VALUES ({placeholders})
            ON CONFLICT (id) DO NOTHING
        """, values)
    except Exception as e:
        print(f"Ошибка при вставке: {e}")

pg_conn.commit()
print(f"✅ Перенесено {len(rows)} записей в catalog_card")

# Проверяем результат
pg_cursor.execute("SELECT COUNT(*) FROM catalog_card")
count = pg_cursor.fetchone()[0]
print(f"Всего записей в PostgreSQL catalog_card: {count}")

# Показываем первые 5 записей для проверки
pg_cursor.execute("SELECT id, title_ru, file_url FROM catalog_card LIMIT 5")
rows = pg_cursor.fetchall()
print("\nПервые 5 записей в PostgreSQL:")
for row in rows:
    print(f"  id={row[0]}, title={row[1]}, file_url={row[2][:50] if row[2] else 'None'}...")

sqlite_conn.close()
pg_conn.close()
print("🎉 Готово!")