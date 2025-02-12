from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite+aiosqlite:///./test.db"  # ✅ Ensure you're using an async-compatible database URL

# ✅ Create async engine
engine = create_async_engine(DATABASE_URL, echo=True)

# ✅ Create session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# ✅ Define Base for models
Base = declarative_base()

# ✅ Function to get a new async session
async def get_async_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
