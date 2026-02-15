from app.api.users.activation import users_router
from app.api.users.avatar import users_router
from app.api.users.login import users_router
from app.api.users.register import users_router
from app.api.users.resend import users_router
from app.api.users.update_status import users_router

__all__ = ["users_router"]
