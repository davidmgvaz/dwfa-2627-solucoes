"""Ficha 03, parte 1 — login e refresh · login and refresh."""

import pytest
from rest_framework.test import APIClient

from accounts.factories import UserFactory


@pytest.mark.django_db
def test_orders_require_auth(client):
    r = client.get("/api/v1/orders/")
    assert r.status_code == 401
    assert r.json()["status"] == 401  # Problem Details envelope


@pytest.mark.django_db
def test_login_returns_pair_and_me_works():
    UserFactory(username="ana", password="pass1234")
    api = APIClient()
    r = api.post("/api/v1/auth/token/", {"username": "ana", "password": "pass1234"})
    assert r.status_code == 200
    body = r.json()
    assert {"access", "refresh"} <= body.keys()
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {body['access']}")
    me = api.get("/api/v1/me/")
    assert me.status_code == 200 and me.json()["username"] == "ana" and me.json()["groups"] == []


@pytest.mark.django_db
def test_refresh_rotates_and_blacklists_old_token():
    UserFactory(username="ana", password="pass1234")
    api = APIClient()
    refresh = api.post("/api/v1/auth/token/", {"username": "ana", "password": "pass1234"}).json()[
        "refresh"
    ]
    r = api.post("/api/v1/auth/token/refresh/", {"refresh": refresh})
    assert r.status_code == 200 and r.json()["refresh"] != refresh
    again = api.post("/api/v1/auth/token/refresh/", {"refresh": refresh})
    assert again.status_code == 401  # blacklisted after rotation
