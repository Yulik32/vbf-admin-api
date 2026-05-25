from database import engine, Base
import models

print("Создание таблиц...")
Base.metadata.create_all(bind=engine)
print("✅ Таблицы созданы")