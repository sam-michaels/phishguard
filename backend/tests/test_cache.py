"""Tests for cache key versioning."""
from app.config import CACHE_VERSION
from app.core.cache import _key


def test_cache_key_includes_version():
    key = _key("https://example.com/")
    assert key.startswith(f"verdict:{CACHE_VERSION}:")


def test_cache_keys_change_when_url_changes():
    k1 = _key("https://example.com/a")
    k2 = _key("https://example.com/b")
    assert k1 != k2
    # But both share the same version prefix
    assert k1.split(":")[1] == k2.split(":")[1] == CACHE_VERSION


def test_cache_key_hash_is_deterministic():
    assert _key("https://example.com/") == _key("https://example.com/")
