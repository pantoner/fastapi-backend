from fastapi.routing import APIRoute
from main import app

print("\n📌 Registered API Routes:")
for route in app.routes:
    print(f"➡️ Path: {route.path} | Methods: {route.methods}")

