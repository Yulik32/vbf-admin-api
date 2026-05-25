import requests

# 1. Логинимся как admin
login_response = requests.post(
    "http://localhost:8000/auth/login",
    json={"email": "admin@example.com", "password": "admin123"}
)

print("1. Логин:")
print(f"   Статус: {login_response.status_code}")
if login_response.status_code == 200:
    token = login_response.json()["access_token"]
    print(f"   Токен получен: {token[:50]}...")
    
    # 2. Проверяем, кто мы
    me_response = requests.get(
        "http://localhost:8000/users/me",  # если такого нет, пропустите
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"\n2. Проверка пользователя: {me_response.status_code}")
    
    # 3. Пытаемся получить список пользователей
    users_response = requests.get(
        "http://localhost:8000/users/",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"\n3. Список пользователей: {users_response.status_code}")
    if users_response.status_code == 200:
        print("   Ответ:", users_response.json())
    else:
        print("   Ошибка:", users_response.text)
else:
    print(f"   Ошибка: {login_response.text}")