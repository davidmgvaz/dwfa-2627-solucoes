from unittest.mock import patch

from django.db import OperationalError
from django.test import TestCase


class HealthTests(TestCase):
    def test_health_ok_when_db_answers(self):
        r = self.client.get("/api/health/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/json")
        self.assertEqual(r.json(), {"status": "ok", "db": "ok"})

    def test_health_503_when_db_is_down(self):
        # PT: simula a base de dados em baixo sem a parar · EN: simulate the DB being down without stopping it
        with patch("core.views.connection.cursor", side_effect=OperationalError("db down")):
            r = self.client.get("/api/health/")
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["db"], "unavailable")
