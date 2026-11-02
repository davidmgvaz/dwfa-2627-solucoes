import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from accounts.factories import UserFactory
from shop.factories import CustomerFactory


@pytest.fixture
def actors(db):
    """anon · customer · gestor — the three columns of the matrix."""
    gestor = UserFactory()
    gestor.groups.add(Group.objects.get(name="gestores"))  # created by migration 0002
    customer = CustomerFactory().user
    return {"anon": None, "customer": customer, "gestor": gestor}


def as_(user):
    api = APIClient()
    if user:
        api.force_authenticate(user=user)
    return api


@pytest.fixture
def customer_api(actors):
    return as_(actors["customer"])
