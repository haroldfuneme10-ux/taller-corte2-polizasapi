"""
polizas-api — Gestión de pólizas y siniestros.
Aseguradora Santo Tomás.

El esquema de la base lo crea Alembic (`alembic upgrade head`), no la aplicación al arrancar.
"""
import hashlib
import pickle
from datetime import date
from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload, selectinload

from config import Settings, get_settings
from database import get_db
from esquemas import (PolizaActualizacion, PolizaEntrada, PolizaSalida, PrediccionSalida,
                      PuntuacionEntrada, PuntuacionSalida, ResumenPoliza, Salud,
                      SiniestroConPoliza, SiniestroEntrada, SiniestroSalida)
from modelos import Poliza, Prediccion, Siniestro

# Parte C: estrategia de carga de cada endpoint con relaciones. Es la que aplica el código de
# abajo; contar_consultas.py la copia a la columna `estrategia` de CONSULTAS.csv.
ESTRATEGIA_CARGA = {
    "/polizas": "selectinload",
    "/polizas/{id}": "lazy",
    "/siniestros": "joinedload",
    "/resumen": "agregada",
}

app = FastAPI(title="Pólizas API", version="1.0.0")


@lru_cache
def cargar_modelo(ruta: str):
    """El modelo se deserializa una sola vez por proceso y por ruta."""
    with open(ruta, "rb") as fh:
        return pickle.load(fh)


def get_modelo(settings: Settings = Depends(get_settings)):
    return cargar_modelo(settings.ruta_modelo)


def firmar(numero: str, secreto: str) -> str:
    return hashlib.sha256(f"{numero}:{secreto}".encode()).hexdigest()


def _buscar_poliza(db: Session, id_poliza: int) -> Poliza:
    poliza = db.get(Poliza, id_poliza)
    if poliza is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no existe la póliza {id_poliza}")
    return poliza


@app.get("/health", response_model=Salud)
def salud(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        base = "ok"
    except SQLAlchemyError:
        base = "error"
    return Salud(estado="ok", base_datos=base)


@app.post("/polizas", response_model=PolizaSalida, status_code=status.HTTP_201_CREATED)
def crear_poliza(datos: PolizaEntrada, db: Session = Depends(get_db),
                 settings: Settings = Depends(get_settings)):
    if db.scalar(select(Poliza.id).where(Poliza.numero == datos.numero)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"ya existe la póliza {datos.numero}")
    poliza = Poliza(**datos.model_dump(exclude={"siniestros"}),
                    token_firma=firmar(datos.numero, settings.secreto_firma),
                    siniestros=[Siniestro(**s.model_dump()) for s in datos.siniestros])
    db.add(poliza)
    try:
        db.commit()
    except IntegrityError:
        # Carrera: otra petición creó el mismo número entre la comprobación y el commit.
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, f"ya existe la póliza {datos.numero}")
    db.refresh(poliza)
    return poliza


@app.get("/polizas", response_model=list[PolizaSalida])
def listar_polizas(db: Session = Depends(get_db)):
    # selectinload: 1 consulta de pólizas + 1 de siniestros con WHERE poliza_id IN (...).
    consulta = select(Poliza).options(selectinload(Poliza.siniestros)).order_by(Poliza.id)
    return db.scalars(consulta).all()


@app.get("/polizas/{id_poliza}", response_model=PolizaSalida)
def obtener_poliza(id_poliza: int, db: Session = Depends(get_db)):
    # lazy: los siniestros se cargan al serializar, con UNA consulta más. Para una sola póliza
    # el total es fijo (2) y no depende del tamaño de la cartera. Ver Parte C.
    return _buscar_poliza(db, id_poliza)


@app.put("/polizas/{id_poliza}", response_model=PolizaSalida)
def actualizar_poliza(id_poliza: int, datos: PolizaActualizacion, db: Session = Depends(get_db)):
    poliza = _buscar_poliza(db, id_poliza)
    cambios = datos.model_dump(exclude_unset=True)
    nueva_fin = cambios.get("fecha_fin", poliza.fecha_fin)
    if nueva_fin <= poliza.fecha_inicio:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            "fecha_fin debe ser posterior a fecha_inicio")
    for campo, valor in cambios.items():
        setattr(poliza, campo, valor)
    db.commit()
    db.refresh(poliza)
    return poliza


@app.post("/polizas/{id_poliza}/siniestros", response_model=SiniestroSalida,
          status_code=status.HTTP_201_CREATED)
def declarar_siniestro(id_poliza: int, datos: SiniestroEntrada, db: Session = Depends(get_db)):
    poliza = _buscar_poliza(db, id_poliza)
    siniestro = Siniestro(poliza=poliza, **datos.model_dump())
    db.add(siniestro)
    db.commit()
    db.refresh(siniestro)
    return siniestro


@app.get("/siniestros", response_model=list[SiniestroConPoliza])
def listar_siniestros(db: Session = Depends(get_db)):
    # joinedload en muchos-a-uno: cada siniestro trae SU póliza en la misma fila (1 consulta).
    consulta = select(Siniestro).options(joinedload(Siniestro.poliza)).order_by(Siniestro.id)
    return db.scalars(consulta).all()


@app.get("/resumen", response_model=list[ResumenPoliza])
def resumen(db: Session = Depends(get_db)):
    # agregada: la base cuenta y suma; no se materializa ningún objeto Siniestro.
    consulta = (
        select(Poliza.numero,
               func.count(Siniestro.id).label("n_siniestros"),
               func.coalesce(func.sum(Siniestro.monto), 0.0).label("monto_total"))
        .outerjoin(Siniestro, Siniestro.poliza_id == Poliza.id)
        .group_by(Poliza.id, Poliza.numero)
        .order_by(Poliza.id)
    )
    return [ResumenPoliza(numero=f.numero, n_siniestros=f.n_siniestros,
                          monto_total=round(f.monto_total, 2))
            for f in db.execute(consulta)]


@app.post("/score", response_model=PuntuacionSalida)
def puntuar(datos: PuntuacionEntrada, db: Session = Depends(get_db),
            settings: Settings = Depends(get_settings), modelo=Depends(get_modelo)):
    poliza = db.scalar(select(Poliza).where(Poliza.numero == datos.numero))
    if poliza is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no existe la póliza {datos.numero}")
    rasgos = [[poliza.prima, len(poliza.siniestros), sum(s.monto for s in poliza.siniestros),
               (date.today() - poliza.fecha_inicio).days]]
    puntaje = float(modelo.predict_proba(rasgos)[0][1])
    prediccion = Prediccion(poliza=poliza, puntaje=puntaje,
                            alto_riesgo=puntaje > settings.umbral_alto_riesgo)
    db.add(prediccion)
    db.commit()
    return PuntuacionSalida(numero=poliza.numero, puntaje=round(puntaje, 4),
                            alto_riesgo=prediccion.alto_riesgo)


@app.get("/predicciones", response_model=list[PrediccionSalida])
def listar_predicciones(db: Session = Depends(get_db)):
    consulta = select(Prediccion).options(joinedload(Prediccion.poliza)).order_by(Prediccion.id)
    return db.scalars(consulta).all()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
