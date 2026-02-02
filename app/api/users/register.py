import secrets

from fastapi import BackgroundTasks, Depends, HTTPException, status
from fastapi_mail import FastMail
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.users.router import users_router
from app.core.database import get_db
from app.core.email import get_mailer_config, prepare_message
from app.core.security import hash_password
from app.models.users import User
from app.schemas.users import UserCreate, UserResponse


@users_router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email, username, and password.",
)
async def register_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Register a new user with the following requirements.

    - **email**: Must be a valid email format.
    - **username**: 3-50 characters, alphanumeric with underscores/hyphens.
    - **password**: Minimum 8 characters,
    must contain uppercase, lowercase, digit, and special char.

    After successful registration, an activation email will be sent
    """

    # Check if user alredy exists
    result = await db.execute(
        select(User).where(
            (User.email == user_data.email)
            | (User.username == user_data.username)
        )
    )
    existing_user = result.scalars().one_or_none()

    if existing_user:
        if existing_user.email == user_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already registered.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is already taken.",
            )

    activation_token = secrets.token_urlsafe(32)

    hashed_password = hash_password(user_data.password)

    new_user = User(
        email=user_data.email,
        username=user_data.username,
        password_hash=hashed_password,
        activation_token=activation_token,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    mailer_config = get_mailer_config()
    fm = FastMail(mailer_config)

    message = prepare_message(new_user.email, activation_token)

    background_tasks.add_task(fm.send_message, message)

    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        username=new_user.username,
        is_active=new_user.is_active,
        created_at=new_user.created_at,
        updated_at=new_user.updated_at,
        is_deleted=new_user.is_deleted,
    )
