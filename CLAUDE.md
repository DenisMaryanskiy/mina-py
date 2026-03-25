# MINA Messenger — Codebase Guide for Claude

## Project Overview
FastAPI messenger backend. Python 3.14, `uv` package manager, PostgreSQL + async SQLAlchemy, Alembic migrations, Redis, RabbitMQ, MinIO (S3-compatible storage). 100% test coverage is required on all new code.

---

## Running Commands
```bash
uv run pytest -v --tb=short --cov --cov-report=term-missing   # run all tests
uv run alembic upgrade head                                    # apply migrations
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000        # start server
```

## Docker
```bash
docker compose up --build   # full stack (postgres, test_postgres, redis, rabbitmq, minio, backend)
```
Backend in Docker runs: `alembic upgrade head && uvicorn ...` at startup.
`ENVIRONMENT=prod` is set in docker-compose so the backend connects to the prod DB, not test DB.

---

## Directory Layout
```
app/
  main.py                  # FastAPI app, includes all routers, adds validation_exception_handler
  core/
    config.py              # Settings (pydantic-settings, reads .env)
    database.py            # SQLAlchemy engine; prod vs dev DB based on ENVIRONMENT env var
    dependencies.py        # get_current_user (raises 401 for bad token, 403 for inactive user)
                           # get_user_from_token_ws; security = HTTPBearer()
    exception.py           # validation_exception_handler: converts 422 → 400
    storage.py             # AvatarStorage, MediaStorage (MinIO wrappers)
    redis.py               # get_redis() — SYNC function returning redis client
    rabbitmq.py
    websocket.py
    lifespan.py
    security.py            # create_access_token, verify_token, hash_password
    logger.py              # get_logger()
    email.py
  models/
    base.py                # Base (DeclarativeBase), TimestampMixin (created_at, updated_at),
                           # IsDeletedMixin (is_deleted bool)
    users.py               # User(Base, TimestampMixin, IsDeletedMixin)
    conversations.py       # Conversation(Base, TimestampMixin) — type, name, avatar_url, created_by, last_message_at
    conversation_participants.py  # ConversationParticipant(Base, TimestampMixin)
                                  # — role ('admin'|'member'), joined_at, last_read_message_id, muted_until, notification_settings(JSONB)
    messages.py            # Message(Base, TimestampMixin, IsDeletedMixin)
    attachments.py         # MessageAttachment(Base) — no soft-delete
    reactions.py           # MessageReaction(Base, TimestampMixin) — no soft-delete
                           # UniqueConstraint(message_id, user_id, emoji)
    __init__.py            # imports all models + __all__ list (Alembic needs this)
  schemas/
    base.py                # GenericMessageResponse, HTTPErrorResponse
    users.py
    conversations.py       # ConversationCreate, ConversationResponse, ConversationListItem
    participants.py        # ParticipantResponse, AddParticipantsRequest
    messages.py            # MessageCreate, MessageEdit, MessageResponse, PaginatedMessages, MessageSearchResponse
    attachments.py         # AttachmentResponse
    reactions.py           # ReactionCreate, ReactionResponse, ReactionSummaryItem, ReactionSummaryResponse
    presence.py
  api/
    conversations/
      router.py            # APIRouter(prefix="/conversations", tags=["Conversations"])
      __init__.py          # imports all handler modules to register routes
      create.py            # POST /conversations
      delete.py            # DELETE /conversations/{id}
      get_by_id.py         # GET /conversations/{id}
      get_by_user.py       # GET /conversations
      participants.py      # POST /conversations/{id}/participants
                           # DELETE /conversations/{id}/participants/{user_id}
    messages/
      router.py            # APIRouter(prefix="/messages", tags=["Messages"])
      __init__.py
      send.py              # POST /conversations/{conv_id}/messages
      get.py               # GET /conversations/{conv_id}/messages (paginated)
      edit.py              # PATCH /messages/{id}
      delete.py            # DELETE /messages/{id}
      mark_read.py         # POST /messages/{id}/read
      search.py            # GET /conversations/{conv_id}/messages/search
      reactions_add.py     # POST /messages/{id}/reactions
      reactions_remove.py  # DELETE /messages/{id}/reactions/{emoji}
      reactions_get.py     # GET /messages/{id}/reactions
    media/
      router.py            # APIRouter(prefix="/media", tags=["Media"])
      __init__.py
      upload.py            # POST /media/upload (avatar)
      attachments.py       # POST /media/attachments, DELETE /media/attachments/{id}
      chunked.py           # POST /media/chunked/init, POST /media/chunked/chunk
    users/
      router.py            # APIRouter(prefix="/users", tags=["Users"])
      __init__.py
      register.py, activation.py, resend.py, login.py, avatar.py, update_status.py, presence.py
    websockets/
      router.py            # APIRouter(prefix="/ws", tags=["WebSockets"])
      __init__.py
      endpoint.py, messages.py
  utils/
    get_active_message.py  # get_active_message(db, message_id) → Message or 404
    require_participant.py # require_participant(db, conv_id, user_id) → ConversationParticipant or 403
  tests/
    conftest.py            # DB engine, migrations fixture (session-scoped, downgrade→upgrade),
                           # async_session (per-test transaction rollback), override_get_db,
                           # async_client, minio_container, storage/minio fixtures,
                           # seed_user (inactive)
    api/
      conftest.py          # seed_activated_user, seed_activated_users (3 users),
                           # login_user, seed_direct_conversation, seed_group_conversation,
                           # seed_message, test_token/test_user_id
      conversations/test_create.py, test_delete.py, test_get.py, test_participants.py
      messages/test_send.py, test_get.py, test_edit.py, test_delete.py,
               test_mark_read.py, test_search.py, test_reactions.py
      media/conftest.py, test_upload.py, test_attachments.py, test_chunked.py
      users/test_register.py, test_activation.py, test_resend.py, test_login.py,
            test_avatar.py, test_update_status.py, test_presence.py, test_refresh.py
      websockets/test_endpoint.py, test_message.py
    core/test_database.py, test_dependencies.py, test_lifespan.py, test_token.py
         redis/..., rabbitmq/..., storage/..., websocket/...
migrations/
  versions/
    b6e1437c4409_create_users_table.py
    81ee78e878a1_create_conversations_participants_and_.py
    e61957fe1201_add_attachments.py
    f3a8c2d91e04_add_message_reactions.py   ← current HEAD
  env.py   # uses settings.ENVIRONMENT to pick prod vs test DB URL
```

---

## Key Patterns & Conventions

### Auth Pattern (every protected endpoint)
```python
from app.core.dependencies import get_current_user, security
current_user = await get_current_user(credentials.credentials, db)
# Raises 401 for invalid/expired token, 403 for inactive/deleted user
```

### Router Registration Pattern
Each feature module registers its own route on the shared router object imported from `router.py`.
The `__init__.py` of each API package imports all handler modules (side-effect imports) and re-exports the router:
```python
# app/api/foo/__init__.py
from app.api.foo.handler_a import foo_router
from app.api.foo.handler_b import foo_router
__all__ = ["foo_router"]
```

### Validation Error Handling
`app/core/exception.py` converts Pydantic `RequestValidationError` (422) → HTTP 400.
Tests asserting validation failures must use `status_code == 400`, NOT 422.

### Unauthenticated Requests
No `Authorization` header → returns **401** (HTTPBearer with `auto_error=True`).
Bad/expired token → `get_current_user` raises **401**.
**Always assert 401 for unauthenticated tests** (no token or bad token).

### Database Session (tests)
Tests use `async_session` fixture: wraps each test in a transaction that is rolled back at the end. `expire_on_commit=False` is set on the test session.
**Important**: SQLAlchemy identity map may cache stale data. When testing code that reads freshly-written rows in the same session, use explicit `select()` queries rather than relying on relationship lazy/selectin load.

### Model Conventions
- `Base` + `TimestampMixin` (created_at, updated_at) for most models
- `IsDeletedMixin` (is_deleted) for soft-delete models: User, Message
- Hard-delete models (no IsDeletedMixin): MessageAttachment, MessageReaction, ConversationParticipant
- UUIDs as PKs with `server_default=text("uuid_generate_v4()")`
- FKs use `ondelete="CASCADE"` or `ondelete="SET NULL"` as appropriate

### Migration Conventions
- New migration `down_revision` = previous HEAD revision
- Current migration HEAD: `f3a8c2d91e04`
- Trigger for `updated_at`:
  ```python
  op.execute("""
      CREATE TRIGGER update_{table}_updated_at
      BEFORE UPDATE ON {table}
      FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
  """)
  ```
- Downgrade: drop trigger → drop indexes → drop table

### Schema Conventions
- Response schemas use `ConfigDict(from_attributes=True)`
- `metadata` column is named `metadata_` in ORM (reserved name), aliased in schema with `alias="metadata_"`
- `HTTPErrorResponse` used for all error responses in OpenAPI docs

### `get_redis()` is SYNC (not async)
```python
from app.core.redis import get_redis
redis_client = get_redis()  # NOT await get_redis()
```
When patching in tests: `patch("...get_redis", return_value=AsyncMock(...))` — no `new_callable=AsyncMock`.

---

## Roadmap Progress

### ✅ Completed
- **§1.1** Real-Time Communication Layer (WebSocket, Redis pub/sub, RabbitMQ)
- **§1.2** Conversations & Direct Messaging (full CRUD, pagination, read receipts, edit/delete, search)
- **§1.3** Presence & Typing Indicators (Redis-backed presence, WebSocket events)
- **§2.1** Media & File Sharing (attachments, chunked upload, thumbnails, virus scan)
- **§2.2** Message Reactions (add/remove/get emoji reactions, 100% coverage)

### 🔲 Next: §2.3 Group Chat Management
**Branch**: `feat/group-chat-management`

**DB changes needed**:
```sql
-- Extend conversations table
ALTER TABLE conversations ADD COLUMN description TEXT;
ALTER TABLE conversations ADD COLUMN is_public BOOLEAN DEFAULT FALSE;
ALTER TABLE conversations ADD COLUMN max_participants INTEGER DEFAULT 1000;
ALTER TABLE conversations ADD COLUMN settings JSONB;

-- New table
CREATE TABLE pinned_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    pinned_by UUID NOT NULL REFERENCES users(id),
    pinned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(conversation_id, message_id)
);
```

**API endpoints**:
- `PATCH /api/v1/groups/{id}` — Update group info (name, avatar, description, is_public, max_participants, settings). Admin only.
- `PATCH /api/v1/groups/{id}/members/{user_id}` — Update member role (promote/demote). Admin only.
- `POST /api/v1/groups/{id}/leave` — Leave group (last admin must transfer or group dissolves).
- `POST /api/v1/messages/{id}/pin` — Pin message. Admin only.
- `DELETE /api/v1/messages/{id}/pin` — Unpin message. Admin only.

**Note**: `POST /groups` (create group) is already handled by `POST /conversations` with `type="group"`.
`POST /groups/{id}/members` is already `POST /conversations/{id}/participants`.
`DELETE /groups/{id}/members/{user_id}` is already `DELETE /conversations/{id}/participants/{user_id}`.

### Future Phases
- **§3.1** Contacts & Friend System
- **§3.2** User Profiles & Privacy
- **§3.3** Search & Discovery

---

## Infrastructure (docker-compose.yaml)
| Service | Port | Notes |
|---------|------|-------|
| postgres | 5432 | main DB |
| test_postgres | 5433 | test DB (local dev only) |
| redis | 6379 | requires auth via REDIS_PASSWORD |
| rabbitmq | 5672, 15672 | management UI on 15672 |
| minio | 9000, 9001 | console on 9001 |
| backend | 8000 | depends_on all services healthy |

All services have healthchecks. Backend waits for healthy deps before starting.
RabbitMQ healthcheck uses `rabbitmq-diagnostics -q check_port_connectivity` (not `ping` — that passes before AMQP port is ready).

---

## Known Gotchas
1. **Validation errors are 400, not 422** — custom handler in `app/core/exception.py`
2. **`get_redis()` is sync** — don't `await` it, don't patch with `new_callable=AsyncMock`
3. **SQLAlchemy identity map caching** — use explicit `select()` in handlers that need fresh data after writes in the same session (see `reactions_get.py`)
4. **Test session `expire_on_commit=False`** — relationships loaded before a commit won't auto-expire; re-query if needed
5. **`ENVIRONMENT=prod` required in Docker** — `database.py` switches to test DB if not prod
6. **migrations/env.py** — uses `settings.ENVIRONMENT` as default for DB URL selection
7. **Black** is a pre-commit hook — if it reformats files, re-stage and re-commit
8. **UV_LINK_MODE=copy** — needed in Dockerfile to avoid hardlink warnings in Docker volumes
