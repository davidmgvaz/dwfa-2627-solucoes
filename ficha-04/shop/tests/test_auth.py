"""Ficha 03, partes 2–4 — a matriz endpoint × papel executada · the matrix, row by row."""

from decimal import Decimal

import pytest

from shop.factories import CategoryFactory, OrderFactory, OrderItemFactory, ProductFactory
from shop.models import Order

from .conftest import as_


@pytest.mark.parametrize("role,expected", [("anon", 401), ("customer", 403), ("gestor", 201)])
def test_create_product_by_role(actors, role, expected):
    body = {
        "name": "Lamp",
        "sku": "L-1",
        "price": "9.90",
        "stock": 3,
        "category": CategoryFactory().id,
    }
    assert as_(actors[role]).post("/api/v1/products/", body).status_code == expected


@pytest.mark.parametrize("role,expected", [("anon", 200), ("customer", 200), ("gestor", 200)])
def test_product_list_is_public(actors, role, expected):
    ProductFactory()
    assert as_(actors[role]).get("/api/v1/products/").status_code == expected


@pytest.mark.parametrize("role,expected", [("anon", 401), ("customer", 1), ("gestor", 3)])
def test_order_list_is_filtered_by_owner(actors, role, expected):
    OrderFactory(customer=actors["customer"].customer)
    OrderFactory.create_batch(2)  # other customers' orders
    r = as_(actors[role]).get("/api/v1/orders/")
    if role == "anon":
        assert r.status_code == expected
    else:
        assert r.status_code == 200 and r.json()["count"] == expected


@pytest.mark.parametrize("path", ["", "pay/"])
def test_foreign_order_is_404_for_customer(actors, path):
    other = OrderFactory()
    api = as_(actors["customer"])
    method = api.post if path else api.get
    assert method(f"/api/v1/orders/{other.id}/{path}").status_code == 404


@pytest.mark.parametrize("role,expected", [("anon", 401), ("customer", 403), ("gestor", 200)])
def test_customers_are_for_gestores_only(actors, role, expected):
    assert as_(actors[role]).get("/api/v1/customers/").status_code == expected


def test_owner_cannot_patch_status(actors):
    order = OrderFactory(customer=actors["customer"].customer)
    OrderItemFactory(order=order, product=ProductFactory(price=Decimal("5.00")))
    r = as_(actors["customer"]).patch(f"/api/v1/orders/{order.id}/", {"status": "paid"})
    assert r.status_code == 200
    order.refresh_from_db()
    assert order.status == Order.Status.PENDING  # read-only: silently ignored


def test_create_order_sets_owner_from_request(actors):
    other = OrderFactory().customer
    r = as_(actors["customer"]).post("/api/v1/orders/", {"customer": other.id})
    assert r.status_code == 201
    assert Order.objects.get(pk=r.json()["id"]).customer.user_id == actors["customer"].id


def test_gestor_sees_and_pays_any_order(actors):
    order = OrderFactory()
    OrderItemFactory(order=order, product=ProductFactory(price=Decimal("5.00")))
    api = as_(actors["gestor"])
    assert api.get(f"/api/v1/orders/{order.id}/").status_code == 200
    assert api.post(f"/api/v1/orders/{order.id}/pay/").status_code == 200
