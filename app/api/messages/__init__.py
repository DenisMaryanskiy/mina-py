from app.api.messages.delete import messages_router
from app.api.messages.edit import messages_router
from app.api.messages.get import messages_router
from app.api.messages.mark_read import messages_router
from app.api.messages.search import messages_router
from app.api.messages.send import messages_router

__all__ = ["messages_router"]
