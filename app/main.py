import os

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.api.conversations import conversations_router
from app.api.messages import messages_router
from app.api.users import users_router
from app.api.websockets import ws_router
from app.core.config import get_settings
from app.core.exception import validation_exception_handler
from app.core.lifespan import lifespan

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
    lifespan=lifespan,
)

app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.include_router(users_router)
app.include_router(ws_router)
app.include_router(conversations_router)
app.include_router(messages_router)
