from app.core.storage import AvatarStorage


def test_get_public_url_with_http(storage: AvatarStorage):
    object_name = "user123/avatar.jpg"

    url = storage._get_public_url(storage.bucket_name, object_name)

    assert url.startswith("http://")
    assert storage.bucket_name in url
    assert object_name in url
