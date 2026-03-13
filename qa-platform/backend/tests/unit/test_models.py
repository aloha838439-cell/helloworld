"""
Unit tests for all ORM models — C1 (User) and C2 (Defect/Change/ImpactAnalysis/TestCase).
Uses an in-memory SQLite database for speed and isolation.
"""
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

# Import Base first so metadata is available
from src.models.base import Base

# Import all models so their tables are registered on Base.metadata
from src.models.user import User
from src.models.defect import Defect
from src.models.change import Change
from src.models.impact_analysis import ImpactAnalysis
from src.models.test_case import TestCase


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def engine():
    """Create an in-memory SQLite engine and create all tables once per module."""
    e = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(e)
    yield e
    Base.metadata.drop_all(e)


@pytest.fixture(scope="module")
def db_session(engine):
    """Provide a SQLAlchemy session bound to the in-memory engine."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="module")
def inspector(engine):
    """SQLAlchemy inspector for schema introspection."""
    return inspect(engine)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def column_names(inspector, table_name):
    """Return a set of column names for a given table."""
    return {col["name"] for col in inspector.get_columns(table_name)}


def get_column(inspector, table_name, col_name):
    """Return the column dict for a specific column."""
    for col in inspector.get_columns(table_name):
        if col["name"] == col_name:
            return col
    return None


# ---------------------------------------------------------------------------
# C1 — User model tests
# ---------------------------------------------------------------------------

class TestUserModel:
    """Tests for the User ORM model (Cycle C1)."""

    def test_user_table_columns(self, inspector):
        """users table must contain id, email, hashed_password, username, is_active, is_admin, created_at."""
        cols = column_names(inspector, "users")
        required = {"id", "email", "hashed_password", "username", "is_active", "is_admin", "created_at"}
        missing = required - cols
        assert missing == set(), f"Missing columns in 'users': {missing}"

    def test_user_email_unique(self, inspector):
        """email column must have a unique constraint."""
        # Check via unique indexes on the users table
        unique_indexes = inspector.get_unique_constraints("users")
        unique_cols_from_indexes = set()
        for uc in unique_indexes:
            unique_cols_from_indexes.update(uc["column_names"])

        # SQLAlchemy also creates unique constraints from unique=True on Column,
        # which in SQLite appear as unique indexes rather than named constraints.
        indexes = inspector.get_indexes("users")
        for idx in indexes:
            if idx.get("unique"):
                unique_cols_from_indexes.update(idx["column_names"])

        assert "email" in unique_cols_from_indexes, (
            "email column should have a unique constraint or unique index"
        )

    def test_user_is_active_default_true(self, db_session):
        """is_active should default to True when a User is created without specifying it."""
        user = User(
            email="default_check@example.com",
            username="defaultuser",
            hashed_password="hashed_placeholder",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.is_active is True
        db_session.delete(user)
        db_session.commit()

    def test_user_is_admin_default_false(self, db_session):
        """is_admin should default to False when a User is created without specifying it."""
        user = User(
            email="admin_check@example.com",
            username="nonadmin",
            hashed_password="hashed_placeholder",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.is_admin is False
        db_session.delete(user)
        db_session.commit()

    def test_user_email_unique_constraint_enforced(self, db_session):
        """Inserting two users with the same email must raise an IntegrityError."""
        from sqlalchemy.exc import IntegrityError

        user1 = User(email="dup@example.com", username="user_one", hashed_password="hash1")
        db_session.add(user1)
        db_session.commit()

        user2 = User(email="dup@example.com", username="user_two", hashed_password="hash2")
        db_session.add(user2)

        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()
        # Clean up user1
        db_session.delete(db_session.query(User).filter_by(email="dup@example.com").first())
        db_session.commit()

    def test_user_created_at_auto_populated(self, db_session):
        """created_at should be populated automatically upon insert."""
        user = User(
            email="timestamp@example.com",
            username="tsuser",
            hashed_password="hash_ts",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.created_at is not None
        db_session.delete(user)
        db_session.commit()

    def test_user_id_is_primary_key(self, inspector):
        """id column must be the primary key of the users table."""
        pk_cols = inspector.get_pk_constraint("users")["constrained_columns"]
        assert "id" in pk_cols


# ---------------------------------------------------------------------------
# C2 — Defect model tests
# ---------------------------------------------------------------------------

class TestDefectModel:
    """Tests for the Defect ORM model (Cycle C2)."""

    def test_defect_table_columns(self, inspector):
        """defects table must contain id, title, description, severity, status, embedding."""
        cols = column_names(inspector, "defects")
        required = {"id", "title", "description", "severity", "status", "embedding", "created_at"}
        missing = required - cols
        assert missing == set(), f"Missing columns in 'defects': {missing}"

    def test_defect_severity_default(self, db_session):
        """severity should default to 'Medium'."""
        defect = Defect(
            title="Default severity defect",
            description="Testing default severity",
            module="TestModule",
        )
        db_session.add(defect)
        db_session.commit()
        db_session.refresh(defect)

        assert defect.severity == "Medium"
        db_session.delete(defect)
        db_session.commit()

    def test_defect_status_default(self, db_session):
        """status should default to 'Open'."""
        defect = Defect(
            title="Default status defect",
            description="Testing default status",
            module="Auth",
        )
        db_session.add(defect)
        db_session.commit()
        db_session.refresh(defect)

        assert defect.status == "Open"
        db_session.delete(defect)
        db_session.commit()

    def test_defect_embedding_can_store_json_array(self, db_session):
        """embedding column (JSON) should be able to store and retrieve a list of floats."""
        embedding_data = [0.1, 0.2, 0.3, 0.4, 0.5]
        defect = Defect(
            title="Embedding defect",
            description="Testing embedding storage",
            module="ML",
            embedding=embedding_data,
        )
        db_session.add(defect)
        db_session.commit()
        db_session.refresh(defect)

        assert defect.embedding == embedding_data
        db_session.delete(defect)
        db_session.commit()

    def test_defect_reporter_id_fk_to_users(self, inspector):
        """reporter_id column must be a foreign key referencing users.id."""
        fks = inspector.get_foreign_keys("defects")
        fk_cols = {fk["constrained_columns"][0]: fk["referred_table"] for fk in fks}
        assert "reporter_id" in fk_cols, "reporter_id should be a FK in defects"
        assert fk_cols["reporter_id"] == "users"

    def test_defect_id_is_primary_key(self, inspector):
        """id must be the primary key of the defects table."""
        pk_cols = inspector.get_pk_constraint("defects")["constrained_columns"]
        assert "id" in pk_cols


# ---------------------------------------------------------------------------
# C2 — Change model tests
# ---------------------------------------------------------------------------

class TestChangeModel:
    """Tests for the Change ORM model (Cycle C2)."""

    def test_change_table_columns(self, inspector):
        """changes table must contain id, description, module, change_type, author, created_at."""
        cols = column_names(inspector, "changes")
        required = {"id", "description", "module", "change_type", "author", "created_at"}
        missing = required - cols
        assert missing == set(), f"Missing columns in 'changes': {missing}"

    def test_change_type_default(self, db_session):
        """change_type should default to 'Feature'."""
        change = Change(description="New feature added", module="Payment")
        db_session.add(change)
        db_session.commit()
        db_session.refresh(change)

        assert change.change_type == "Feature"
        db_session.delete(change)
        db_session.commit()

    def test_change_user_id_fk_to_users(self, inspector):
        """user_id column must be a FK referencing users.id."""
        fks = inspector.get_foreign_keys("changes")
        fk_cols = {fk["constrained_columns"][0]: fk["referred_table"] for fk in fks}
        assert "user_id" in fk_cols, "user_id should be a FK in changes"
        assert fk_cols["user_id"] == "users"


# ---------------------------------------------------------------------------
# C2 — ImpactAnalysis model tests
# ---------------------------------------------------------------------------

class TestImpactAnalysisModel:
    """Tests for the ImpactAnalysis ORM model (Cycle C2)."""

    def test_impact_analysis_table_columns(self, inspector):
        """impact_analyses table must have key columns."""
        cols = column_names(inspector, "impact_analyses")
        required = {"id", "user_id", "change_id", "query_description", "impact_score", "risk_level", "created_at"}
        missing = required - cols
        assert missing == set(), f"Missing columns in 'impact_analyses': {missing}"

    def test_impact_analysis_fk_to_changes(self, inspector):
        """change_id must be a FK referencing the changes table."""
        fks = inspector.get_foreign_keys("impact_analyses")
        fk_map = {fk["constrained_columns"][0]: fk["referred_table"] for fk in fks}
        assert "change_id" in fk_map, "change_id should be a FK in impact_analyses"
        assert fk_map["change_id"] == "changes"

    def test_impact_analysis_fk_to_users(self, inspector):
        """user_id must be a FK referencing the users table."""
        fks = inspector.get_foreign_keys("impact_analyses")
        fk_map = {fk["constrained_columns"][0]: fk["referred_table"] for fk in fks}
        assert "user_id" in fk_map, "user_id should be a FK in impact_analyses"
        assert fk_map["user_id"] == "users"

    def test_impact_score_is_float_type(self, inspector):
        """impact_score column must be a numeric (Float) type."""
        col = get_column(inspector, "impact_analyses", "impact_score")
        assert col is not None, "impact_score column not found"
        # SQLAlchemy Float maps to REAL or FLOAT in SQLite
        type_name = type(col["type"]).__name__.upper()
        assert type_name in ("FLOAT", "REAL", "NUMERIC", "DOUBLE", "DOUBLEPRECISION"), (
            f"Unexpected type for impact_score: {type_name}"
        )

    def test_impact_score_default_zero(self, db_session):
        """impact_score should default to 0.0."""
        analysis = ImpactAnalysis(query_description="Default score test")
        db_session.add(analysis)
        db_session.commit()
        db_session.refresh(analysis)

        assert analysis.impact_score == 0.0
        db_session.delete(analysis)
        db_session.commit()

    def test_risk_level_default(self, db_session):
        """risk_level should default to 'Low'."""
        analysis = ImpactAnalysis(query_description="Risk level default test")
        db_session.add(analysis)
        db_session.commit()
        db_session.refresh(analysis)

        assert analysis.risk_level == "Low"
        db_session.delete(analysis)
        db_session.commit()


# ---------------------------------------------------------------------------
# C2 — TestCase model tests
# ---------------------------------------------------------------------------

class TestTestCaseModel:
    """Tests for the TestCase ORM model (Cycle C2)."""

    def test_test_case_table_columns(self, inspector):
        """test_cases table must contain key columns."""
        cols = column_names(inspector, "test_cases")
        required = {"id", "analysis_id", "title", "description", "steps", "priority", "test_type", "created_at"}
        missing = required - cols
        assert missing == set(), f"Missing columns in 'test_cases': {missing}"

    def test_test_case_fk_to_impact_analyses(self, inspector):
        """analysis_id must be a FK referencing the impact_analyses table."""
        fks = inspector.get_foreign_keys("test_cases")
        fk_map = {fk["constrained_columns"][0]: fk["referred_table"] for fk in fks}
        assert "analysis_id" in fk_map, "analysis_id should be a FK in test_cases"
        assert fk_map["analysis_id"] == "impact_analyses"

    def test_test_case_priority_default(self, db_session):
        """priority should default to 'Medium'."""
        tc = TestCase(title="Default priority test case")
        db_session.add(tc)
        db_session.commit()
        db_session.refresh(tc)

        assert tc.priority == "Medium"
        db_session.delete(tc)
        db_session.commit()

    def test_test_case_type_default(self, db_session):
        """test_type should default to 'Functional'."""
        tc = TestCase(title="Default type test case")
        db_session.add(tc)
        db_session.commit()
        db_session.refresh(tc)

        assert tc.test_type == "Functional"
        db_session.delete(tc)
        db_session.commit()

    def test_test_case_steps_can_store_json_list(self, db_session):
        """steps column (JSON) should store and retrieve a list of step strings."""
        steps = ["Step 1: Navigate to login", "Step 2: Enter credentials", "Step 3: Click submit"]
        tc = TestCase(title="Steps storage test", steps=steps)
        db_session.add(tc)
        db_session.commit()
        db_session.refresh(tc)

        assert tc.steps == steps
        db_session.delete(tc)
        db_session.commit()


# ---------------------------------------------------------------------------
# Import completeness test
# ---------------------------------------------------------------------------

class TestModelsInit:
    """Verify that all 5 models are importable from src.models."""

    def test_models_init_imports_all(self):
        """All 5 models (User, Defect, Change, ImpactAnalysis, TestCase) must be importable from src.models."""
        import src.models as models_pkg

        for name in ("User", "Defect", "Change", "ImpactAnalysis", "TestCase"):
            assert hasattr(models_pkg, name), f"src.models does not export '{name}'"

    def test_all_models_have_tablename(self):
        """Every model class must define __tablename__."""
        for cls in (User, Defect, Change, ImpactAnalysis, TestCase):
            assert hasattr(cls, "__tablename__"), f"{cls.__name__} is missing __tablename__"

    def test_base_metadata_contains_all_tables(self):
        """Base.metadata should contain all 5 table names after import."""
        expected_tables = {"users", "defects", "changes", "impact_analyses", "test_cases"}
        actual_tables = set(Base.metadata.tables.keys())
        missing = expected_tables - actual_tables
        assert missing == set(), f"Missing tables in Base.metadata: {missing}"
