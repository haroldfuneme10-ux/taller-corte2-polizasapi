"""Conexión a la base de datos: un motor por proceso y una sesión POR PETICIÓN."""
from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import get_settings


class Base(DeclarativeBase):
    pass


def crear_motor(url: str):
    """Motor para `url`. En SQLite activa las claves foráneas en CADA conexión nueva."""
    es_sqlite = url.startswith("sqlite")
    motor = create_engine(url, connect_args={"check_same_thread": False} if es_sqlite else {})
    if es_sqlite:
        @event.listens_for(motor, "connect")
        def _activar_claves_foraneas(conexion_dbapi, _registro):
            # SQLite trae las FK desactivadas por defecto y el PRAGMA es por conexión.
            cursor = conexion_dbapi.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return motor


engine = crear_motor(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


def get_db() -> Iterator[Session]:
    """Dependencia de FastAPI: abre una sesión para la petición y la cierra siempre al terminar.

    Si la petición falla a mitad de una transacción, `close()` la revierte: el error no
    contamina a las peticiones siguientes (lo que sí pasaba con la sesión global).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
