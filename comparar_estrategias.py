"""
Parte C · exploración previa a la decisión: cuenta las consultas de CADA estrategia posible
para los cuatro endpoints, no solo de la que quedó en main.py.

    python comparar_estrategias.py                  # 10 y 2000 pólizas
    python comparar_estrategias.py --tamanos 10 200

Usa el mismo contador que contar_consultas.py (`before_cursor_execute`) sobre una base
temporal sembrada por la API, y serializa con los mismos esquemas de salida que la API,
así que los lazy loads que dispara la serialización también se cuentan. El tiempo es el
mejor de tres repeticiones y solo sirve para comparar dentro de una misma máquina.
"""
import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tamanos", nargs="+", type=int, default=[10, 2000])
    a = ap.parse_args()

    raiz = Path(__file__).parent.resolve()
    os.chdir(raiz)
    sys.path.insert(0, str(raiz))
    db = Path(tempfile.mkdtemp(prefix="comparar-")) / "comparar.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db}"
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True,
                   capture_output=True)

    from fastapi.testclient import TestClient
    from sqlalchemy import event, func, select
    from sqlalchemy.engine import Engine
    from sqlalchemy.orm import joinedload, selectinload

    from database import SessionLocal
    from esquemas import PolizaSalida, SiniestroConPoliza
    from main import app
    from modelos import Poliza, Siniestro
    from sembrar_datos import sembrar

    contador = {"n": 0}

    @event.listens_for(Engine, "before_cursor_execute")
    def _contar(*_):
        contador["n"] += 1

    cargas = {"lazy": None, "selectinload": selectinload, "joinedload": joinedload}

    def polizas(carga):
        with SessionLocal() as s:
            q = select(Poliza).order_by(Poliza.id)
            if carga:
                q = q.options(carga(Poliza.siniestros))
            filas = s.scalars(q).unique()
            return [PolizaSalida.model_validate(p).model_dump() for p in filas]

    def una_poliza(carga):
        with SessionLocal() as s:
            p = s.get(Poliza, 1, options=[carga(Poliza.siniestros)] if carga else None)
            return PolizaSalida.model_validate(p).model_dump()

    def siniestros(carga):
        with SessionLocal() as s:
            q = select(Siniestro).order_by(Siniestro.id)
            if carga:
                q = q.options(carga(Siniestro.poliza))
            return [SiniestroConPoliza.model_validate(x).model_dump() for x in s.scalars(q)]

    def resumen(carga):
        with SessionLocal() as s:
            if carga == "agregada":
                q = (select(Poliza.numero, func.count(Siniestro.id),
                            func.coalesce(func.sum(Siniestro.monto), 0.0))
                     .outerjoin(Siniestro, Siniestro.poliza_id == Poliza.id)
                     .group_by(Poliza.id, Poliza.numero).order_by(Poliza.id))
                return [(n, c, round(m, 2)) for n, c, m in s.execute(q)]
            q = select(Poliza).order_by(Poliza.id)
            if carga:
                q = q.options(carga(Poliza.siniestros))
            return [(p.numero, len(p.siniestros), round(sum(x.monto for x in p.siniestros), 2))
                    for p in s.scalars(q).unique()]

    def medir(f, carga):
        f(carga)  # calentamiento
        mejor = float("inf")
        for _ in range(3):
            contador["n"] = 0
            t0 = time.perf_counter()
            f(carga)
            mejor = min(mejor, (time.perf_counter() - t0) * 1000)
        return contador["n"], mejor

    casos = [("/polizas", polizas, cargas), ("/polizas/{id}", una_poliza, cargas),
             ("/siniestros", siniestros, cargas),
             ("/resumen", resumen, {**cargas, "agregada": "agregada"})]

    print(f"{'endpoint':<15} {'estrategia':<13} {'n_polizas':>9} {'consultas':>9} {'ms':>8}")
    with TestClient(app) as cliente:
        sembradas = 0
        for n in a.tamanos:
            sembrar(cliente, n - sembradas, 3, prefijo="POL-C", desde=sembradas + 1)
            sembradas = n
            for endpoint, f, opciones in casos:
                for nombre, carga in opciones.items():
                    consultas, ms = medir(f, carga)
                    print(f"{endpoint:<15} {nombre:<13} {n:>9} {consultas:>9} {ms:>8.1f}")


if __name__ == "__main__":
    main()
