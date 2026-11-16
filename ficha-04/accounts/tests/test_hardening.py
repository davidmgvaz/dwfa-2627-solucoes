"""Ficha 03, parte 3 — CORS, throttling, hashers · hardening."""

import pytest
from django.conf import settings
from django.core.cache import cache
from rest_framework.test import APIClient


def test_argon2_is_the_default_hasher_outside_tests():
    # test.py overrides PASSWORD_HASHERS with MD5 on purpose; check base.py's intent instead
    from config.settings import base

    assert base.PASSWORD_HASHERS[0].endswith("Argon2PasswordHasher")
    assert base.AUTH_PASSWORD_VALIDATORS[1]["OPTIONS"] == {"min_length": 12}


def test_cors_allowlist_is_explicit():
    assert "http://localhost:5173" in settings.CORS_ALLOWED_ORIGINS
    assert not getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False)
    assert settings.MIDDLEWARE[0] == "corsheaders.middleware.CorsMiddleware"


@pytest.mark.django_db
def test_cors_preflight_from_the_spa_origin():
    r = APIClient().options(
        "/api/v1/orders/",
        HTTP_ORIGIN="http://localhost:5173",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
    )
    assert r.status_code == 200
    assert r["Access-Control-Allow-Origin"] == "http://localhost:5173"


@pytest.mark.django_db
def test_login_is_throttled_after_ten_attempts():
    cache.clear()
    api = APIClient()
    codes = [
        api.post("/api/v1/auth/token/", {"username": "x", "password": "x"}).status_code
        for _ in range(11)
    ]
    assert codes[:10] == [401] * 10 and codes[10] == 429
    cache.clear()
