import os

from fastapi import FastAPI

from app.api.users import users_router
from app.core.config import get_settings

os.environ.setdefault("ENVIRONMENT", os.getenv("ENVIRONMENT", "dev"))
settings = get_settings()  # Load settings based on the environment

app = FastAPI(
    title="MINA Application",
    debug=settings.ENVIRONMENT == "dev",
    summary="""A messenger-social network which uses best practices in
        messaging like Telegram or WhatsApp and which uses best practices
        for social network systems like Facebook""",
    description="""MINA is built with FastAPI and PostgreSQL,
        focusing on performance, scalability, and developer experience.""",
    version="0.1.0",
    openapi_version="3.1.0",
    root_path="/api/v1",
)

app.include_router(users_router)
