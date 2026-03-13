"""
Integration tests for Alembic database migrations — Cycle C3.

These tests run actual alembic CLI commands (upgrade/downgrade) against
a real database to verify migration correctness and idempotency.

The database URL is resolved from:
  1. DATABASE_URL environment variable
  2. fallback: sqlite:///./test.db
"""
import os
import subprocess
import sys
import pytest
from sqlalchemy import create_engine, inspect, text


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXPECTED_TABLES = {"users", "defects", "changes", "impact_analyses", "test_cases"}

# Path to the backend directory (where alembic.ini lives)
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
BACKEND_DIR = os.path.abspath(BACKEND_DIR)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def database_url():
    """Resolve the test DATABASE_URL with SQLite fallback."""
    url = os.getenv("DATABASE_URL", "sqlite:///./test.db")
    return url


@pytest.fixture(scope="module")
def db_engine(database_url):
    """Create a SQLAlchemy engine connected to the test database."""
    # SQLite requires special connect_args; other databases don't
    if database_url.startswith("sqlite"):
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
        )
    else:
        engine = create_engine(database_url)

    yield engine
    engine.dispose()


def run_alembic(args, cwd=BACKEND_DIR, database_url=None):
    """
    Run an alembic CLI command and return the CompletedProcess.

    Args:
        args: list of alembic sub-command arguments, e.g. ["upgrade", "head"]
        cwd:  working directory (should contain alembic.ini)
        database_url: optional DATABASE_URL override passed as env var
    """
    env = os.environ.copy()
    if database_url:
        env["DATABASE_URL"] = database_url
    # Ensure the src package is importable from the backend directory
    pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = BACKEND_DIR + (os.pathsep + pythonpath if pythonpath else "")

    result = subprocess.run(
        [sys.executable, "-m", "alembic"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
    )
    return result


def get_existing_tables(engine):
    """Return the set of table names currently in the database."""
    insp = inspect(engine)
    return set(insp.get_table_names())


# ---------------------------------------------------------------------------
# C3 — Migration tests
# ---------------------------------------------------------------------------

class TestAlembicMigrations:
    """Tests for Alembic upgrade/downgrade migrations (Cycle C3)."""

    def test_alembic_upgrade_head(self, database_url):
        """alembic upgrade head must exit with return code 0."""
        result = run_alembic(["upgrade", "head"], database_url=database_url)
        assert result.returncode == 0, (
            f"alembic upgrade head failed (rc={result.returncode}).\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

    def test_all_tables_exist(self, db_engine, database_url):
        """After upgrade head, all 5 expected tables must be present in the database."""
        # Ensure we are at head first
        run_alembic(["upgrade", "head"], database_url=database_url)

        existing = get_existing_tables(db_engine)
        missing = EXPECTED_TABLES - existing
        assert missing == set(), (
            f"The following tables are missing after 'alembic upgrade head': {missing}\n"
            f"Tables present: {existing}"
        )

    def test_migration_is_idempotent(self, database_url, db_engine):
        """Running alembic upgrade head twice must not raise an error."""
        # First upgrade (already done in test_alembic_upgrade_head, but do it explicitly)
        result1 = run_alembic(["upgrade", "head"], database_url=database_url)
        assert result1.returncode == 0, (
            f"First upgrade head failed.\nSTDERR: {result1.stderr}"
        )

        # Second upgrade — should be a no-op and also return 0
        result2 = run_alembic(["upgrade", "head"], database_url=database_url)
        assert result2.returncode == 0, (
            f"Second (idempotent) upgrade head failed.\nSTDERR: {result2.stderr}"
        )

        # Tables must still be intact
        existing = get_existing_tables(db_engine)
        missing = EXPECTED_TABLES - existing
        assert missing == set(), (
            f"Tables missing after idempotent upgrade: {missing}"
        )

    def test_alembic_downgrade_and_upgrade(self, database_url, db_engine):
        """
        Downgrade by one revision then upgrade back to head.
        All expected tables must be present after the final upgrade.
        """
        # Start at head
        up_result = run_alembic(["upgrade", "head"], database_url=database_url)
        assert up_result.returncode == 0, (
            f"Pre-test upgrade head failed.\nSTDERR: {up_result.stderr}"
        )

        # Downgrade one revision
        down_result = run_alembic(["downgrade", "-1"], database_url=database_url)
        assert down_result.returncode == 0, (
            f"alembic downgrade -1 failed (rc={down_result.returncode}).\n"
            f"STDOUT:\n{down_result.stdout}\n"
            f"STDERR:\n{down_result.stderr}"
        )

        # Upgrade back to head
        reup_result = run_alembic(["upgrade", "head"], database_url=database_url)
        assert reup_result.returncode == 0, (
            f"Re-upgrade head after downgrade failed.\nSTDERR: {reup_result.stderr}"
        )

        # Verify all tables are back
        existing = get_existing_tables(db_engine)
        missing = EXPECTED_TABLES - existing
        assert missing == set(), (
            f"Tables missing after downgrade+upgrade cycle: {missing}\n"
            f"Tables present: {existing}"
        )

    def test_alembic_current_shows_head_after_upgrade(self, database_url):
        """alembic current should output 'head' after a successful upgrade."""
        run_alembic(["upgrade", "head"], database_url=database_url)
        result = run_alembic(["current"], database_url=database_url)
        assert result.returncode == 0, (
            f"alembic current failed.\nSTDERR: {result.stderr}"
        )
        # The output should contain 'head' indicating we are at the latest revision
        output = result.stdout + result.stderr
        assert "head" in output.lower(), (
            f"Expected 'head' in alembic current output, got:\n{output}"
        )
