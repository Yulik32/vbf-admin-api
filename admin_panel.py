# admin_panel.py
import requests

BASE_URL = "http://localhost:8000"

def login(email, password):
    resp = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    if resp.status_code == 200:
        return resp.json()["access_token"]
    return None

def get_users(token):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/users/", headers=headers)
    return resp

def create_card(token, title, description):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(f"{BASE_URL}/cards/", 
                        json={"title": title, "description": description, "order": 1},
                        headers=headers)
    return resp

# Использование
token = login("admin@example.com", "admin123")
if token:
    print("✅ Залогинились")
    
    users = get_users(token)
    if users.status_code == 200:
        print("Пользователи:", users.json())
    else:
        print("Ошибка:", users.status_code, users.text)