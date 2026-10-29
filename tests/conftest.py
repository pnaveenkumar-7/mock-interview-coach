import pytest
from sqlalchemy.pool import StaticPool
from app import create_app
from app.extensions import db


@pytest.fixture(scope="session")
def app():
    """
    Creates an isolated application instance configured with an in-memory SQLite database.
    Session-scoped so the in-memory SQLite database connection remains alive for all tests.
    Guarantees tests never touch instance/app.db or any seeded production data.
    """
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_ENGINE_OPTIONS": {
            "poolclass": StaticPool,
            "connect_args": {"check_same_thread": False},
        },
        "SECRET_KEY": "test-secret-key-for-unit-tests",
    }
    app = create_app(test_config=test_config)

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture(autouse=True)
def clean_tables(app):
    """
    Cleans all database rows before each test, providing complete test isolation.
    """
    with app.app_context():
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()


@pytest.fixture
def client(app):
    """
    Fresh test client for each test function.
    """
    return app.test_client()
