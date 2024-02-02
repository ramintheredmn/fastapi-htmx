import os
from typing import AsyncGenerator
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
import sshtunnel
load_dotenv()

# Environment variables
ENV = os.environ.get("ENV", "prod")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")
SSH_PASSWORD = os.environ.get("SSH_PASSWORD")

# SSH Tunnel for development environment
if ENV == "dev":
    tunnel = sshtunnel.SSHTunnelForwarder(
        ('217.144.106.18'), ssh_username='gadget', ssh_password=SSH_PASSWORD, remote_bind_address=('localhost', 3306)
    )
    tunnel.start()
    LOCAL_BIND_PORT = tunnel.local_bind_port
else:
    LOCAL_BIND_PORT = 3306  # Default port for production

# Database URL configuration
DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASS}@localhost:{LOCAL_BIND_PORT}/gadget" if ENV == "dev" else f"mysql+aiomysql://{DB_USER}:{DB_PASS}@localhost:3306/gadget"

# Create the async engine and sessionmaker
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# Dependency for FastAPI to use in routes
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine) as session:
        yield session
