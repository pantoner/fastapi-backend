from fastapi import FastAPI
from routes.auth import auth_router  # ✅ Import authentication routes

app = FastAPI()

# ✅ Include authentication routes
app.include_router(auth_router, prefix="/auth", tags=["auth"])

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}
