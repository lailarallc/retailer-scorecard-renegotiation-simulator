"""The prod guard sits in front of the Postgres read in scripts/export_data.py.

`_pg_connect()` reads DATABASE_URL, else localhost:5432 -- a `fly proxy` tunnel
to production when one is open. These tests fake a flyctl listener and assert
nothing connects, and that the refusal is raised rather than swallowed by the
fall-back-to-snapshot path.
"""

import sys
from pathlib import Path

import pytest

SCRIPTS = str(Path(__file__).resolve().parent.parent / "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import export_data  # noqa: E402
import prod_guard  # noqa: E402

pytestmark = pytest.mark.skipif(not export_data._HAS_PG, reason="psycopg2 not installed")


@pytest.fixture
def fly_tunnel(monkeypatch):
    for var in ("ALLOW_PROD_DB", "DATABASE_URL", "POSTGRES_PASSWORD", "PGHOST", "PGPORT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(prod_guard, "_listener", lambda port: "flyctl")
    monkeypatch.setattr(export_data.psycopg2, "connect", lambda *a, **kw: pytest.fail("connected"))


def test_database_url_refuses_fly_tunnel(fly_tunnel, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost:5432/db")
    with pytest.raises(prod_guard.ProdDatabaseError):
        export_data._pg_connect()


def test_localhost_default_refuses_fly_tunnel(fly_tunnel, monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "not-a-real-password")
    with pytest.raises(prod_guard.ProdDatabaseError):
        export_data._pg_connect()


def test_refusal_does_not_fall_back_to_snapshot(fly_tunnel, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost:5432/db")
    with pytest.raises(prod_guard.ProdDatabaseError):
        export_data.build_retailer_data()
