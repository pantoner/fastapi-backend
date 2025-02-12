from fastapi import FastAPI, Depends
from fastapi_users import FastAPIUsers
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.authentication.strategy import JWTStrategy
from fastapi_users.authentication import AuthenticationBackend, CookieTransport
from fastapi_users.manager import BaseUserManager
from fastapi_users import UUIDIDMixin
from sqlalchemy.ext.asyncio import AsyncSession
from database import engine, get_async_session, Base
from models.user import User, UserRead, UserCreate, UserUpdate  # ✅ Import Pydantic models

# ✅ Define JWT Transport (Handles token storage in cookies)
jwt_transport = CookieTransport(cookie_max_age=3600)

# ✅ Secret key for JWT tokens
SECRET = "your_secret_key_here"

# ✅ Define JWT Strategy
def get_jwt_strategy():
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)

# ✅ Define authentication backend
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=jwt_transport,
    get_strategy=get_jwt_strategy,
)

# ✅ Create user database adapter as a dependency
async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)

# ✅ Define User Manager (Required for FastAPI Users v14+)
class UserManager(UUIDIDMixin, BaseUserManager[User, int]):
    user_db_model = User
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)

# ✅ FastAPI Users manager (Updated for v14+)
fastapi_users = FastAPIUsers(
    get_user_manager,  # ✅ Use UserManager instead of get_user_db
    [auth_backend],
)

# ✅ Authentication routes
auth_router = fastapi_users.get_auth_router(auth_backend)
register_router = fastapi_users.get_register_router(UserRead, UserCreate)  # ✅ Fixed!

# ✅ Create FastAPI app and include routes
app = FastAPI()
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(register_router, prefix="/auth", tags=["auth"])

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}
