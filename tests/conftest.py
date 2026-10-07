"""Fixtures compartidas: cada test recibe un cliente sobre una base SQLite TEMPORAL y vacía.

La sesión de la aplicación se sustituye con `app.dependency_overrides[database.get_db]`,
de modo que ningún test escribe en la base de la aplicación (app.db).
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))

import database  # noqa: E402
import modelos  # noqa: E402,F401
from main import app  # noqa: E402


@pytest.fixture
def cliente(tmp_path):
    motor = database.crear_motor(f"sqlite:///{tmp_path / 'test.db'}")  # con PRAGMA foreign_keys
    database.Base.metadata.create_all(motor)
    Sesion = sessionmaker(bind=motor, autoflush=False)

    def _get_db():
        db = Sesion()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[database.get_db] = _get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(database.get_db, None)
        motor.dispose()
