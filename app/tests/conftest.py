import io
import os
import secrets
import time
import uuid
from unittest.mock import Mock

import faker
import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from fastapi import UploadFile
from minio import Minio
from PIL import Image
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.minio import DockerContainer

from app.core.config import get_settings
from app.core.database import get_db
from app.core.logger import get_logger
from app.core.security import hash_password
from app.core.storage import MinioStorage
from app.main import app
from app.models.users import User

logger = get_logger()

settings = get_settings()
TEST_DATABASE_URL = f"postgresql+asyncpg://{settings.TEST_POSTGRES_USER}:{settings.TEST_POSTGRES_PASSWORD}@{settings.TEST_POSTGRES_HOST}:{settings.TEST_POSTGRES_PORT}/{settings.TEST_POSTGRES_DB}"

# === Test DB setup ===
engine_test = create_async_engine(TEST_DATABASE_URL, future=True)
TestingSessionLocal = async_sessionmaker(
    engine_test, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture()
async def test_session_engine():
    """Фикстура для мока движка на всю сессию тестов"""
    engine = create_async_engine(TEST_DATABASE_URL)
    yield engine
    await engine.dispose()


# === Apply migrations once ===
@pytest.fixture(scope="session", autouse=True)
def migrate_db():
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


# === DB session per test ===
@pytest_asyncio.fixture()
async def async_session(test_session_engine: AsyncEngine):
    async with test_session_engine.connect() as conn:
        transaction = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
            await conn.close()


# === Dependency override ===
@pytest_asyncio.fixture(autouse=True)
async def override_get_db(async_session):
    async def _get_db():
        yield async_session

    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.clear()


# === Async test client ===
@pytest_asyncio.fixture()
async def async_client():
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        yield client


# === Mock S3 client ===
def pytest_configure(config):
    """Disable Ryuk to prevent port 8080 conflicts."""
    os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"


@pytest.fixture(scope="session")
def minio_container():
    container = DockerContainer("minio/minio:latest")
    container.with_env("MINIO_ROOT_USER", "test_key")
    container.with_env("MINIO_ROOT_PASSWORD", "test_secret")
    container.with_exposed_ports(9000)
    container.with_command("server /data")

    container.start()
    time.sleep(3)

    host = container.get_container_host_ip()
    port = container.get_exposed_port(9000)

    client = Minio(
        f"{host}:{port}",
        access_key="test_key",
        secret_key="test_secret",
        secure=False,
    )

    for _ in range(10):
        try:
            client.list_buckets()
            break
        except Exception:
            time.sleep(1)

    container.config = {
        "endpoint": f"{host}:{port}",
        "access_key": "test_key",
        "secret_key": "test_secret",
    }

    yield container
    container.stop()


@pytest.fixture
def test_bucket_name():
    return f"test-bucket-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def storage(minio_container: DockerContainer, test_bucket_name: str):
    config = minio_container.config

    mock_settings = Mock()
    mock_settings.MINIO_ENDPOINT = config["endpoint"]
    mock_settings.MINIO_ACCESS_KEY = config["access_key"]
    mock_settings.MINIO_SECRET_KEY = config["secret_key"]
    mock_settings.MINIO_SECURE = False
    mock_settings.MINIO_BUCKET_NAME = test_bucket_name
    mock_settings.MINIO_REGION = "us-east-1"
    mock_settings.ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    mock_settings.MAX_IMAGE_SIZE_MB = "5"

    mock_logger = Mock()

    return MinioStorage(settings=mock_settings, logger=mock_logger)


@pytest.fixture
def minio_client(minio_container):
    config = minio_container.config
    return Minio(
        config["endpoint"],
        access_key=config["access_key"],
        secret_key=config["secret_key"],
        secure=False,
    )


@pytest.fixture
def cleanup_bucket(storage, minio_client):
    yield

    # Cleanup after test
    try:
        objects = minio_client.list_objects(storage.bucket_name, recursive=True)
        for obj in objects:
            minio_client.remove_object(storage.bucket_name, obj.object_name)
    except Exception:
        pass


@pytest.fixture
def valid_jpeg_file():
    img = Image.new("RGB", (200, 200), color="blue")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)

    return UploadFile(filename="avatar.jpg", file=img_bytes)


@pytest.fixture
def valid_png_file():
    img = Image.new("RGBA", (150, 150), color="green")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    return UploadFile(filename="profile.png", file=img_bytes)


@pytest.fixture
def large_image_file():
    img = Image.new("RGB", (25000, 25000), color="red")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", quality=100)
    img_bytes.seek(0)

    return UploadFile(filename="large_avatar.jpg", file=img_bytes)


@pytest.fixture
def sample_image() -> io.BytesIO:
    img = Image.new("RGB", (200, 200), color="blue")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)

    return img_bytes


@pytest.fixture
def invalid_extension_file():
    content = b"fake image content"
    file_obj = io.BytesIO(content)

    return UploadFile(filename="document.pdf", file=file_obj)


@pytest.fixture
def corrupted_image_file():
    content = b"This is not a valid image file content"
    file_obj = io.BytesIO(content)

    return UploadFile(filename="corrupted.jpg", file=file_obj)


@pytest.fixture
def test_user_uuid():
    return uuid.UUID("12345678-1234-5678-1234-567812345678")


f = faker.Faker()


@pytest_asyncio.fixture
async def seed_user(async_session: AsyncSession):
    """Seed user into Postgres test DB."""
    u = User(
        id=f.uuid4(),
        username=f.user_name(),
        email=f.email(),
        password_hash=hash_password("S!trongP@ssw0rd!"),
        activation_token=secrets.token_urlsafe(32),
    )
    async_session.add(u)
    await async_session.commit()
    yield u
