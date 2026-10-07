"""Batería de `ia_tests_propuesta.py`, corregida (Parte D · ver DICTAMEN_IA.md).

Qué cambia respecto a la propuesta de la IA:
  1. Cada aserción exige UN resultado: el que dice el contrato (201, 404, 422, 409...).
     Ya no hay `in (200, 201, 422)` ni `< 500`, que aceptan cualquier cosa.
  2. Cada test comprueba lo que su nombre promete, leyendo de vuelta lo persistido
     (la póliza creada se puede consultar, la predicción queda en /predicciones), y el
     aislamiento es real: la fixture `cliente` (tests/conftest.py) sustituye
     `database.get_db` —la dependencia que la app usa de verdad— por una sesión sobre
     una base temporal y vacía. Nada de MagicMock ni de un `get_db` local que nadie usa.
  3. Datos fijos y deterministas: los casos «variados» se enumeran con parametrize
     (todos los tipos, primas en los bordes) en lugar de sortearse en cada corrida.

    pytest tests/test_ia_corregido.py -v
"""
import pytest

TIPOS = ["auto", "hogar", "vida"]


def _poliza(numero: str = "POL-IA-00001", **extra) -> dict:
    base = {
        "numero": numero,
        "asegurado": "Prueba Automática",
        "tipo": "auto",
        "prima": 1_250_000,
        "fecha_inicio": "2026-01-01",
        "fecha_fin": "2026-12-31",
    }
    base.update(extra)
    return base


def _crear(cliente, **extra) -> dict:
    r = cliente.post("/polizas", json=_poliza(**extra))
    assert r.status_code == 201, f"crear devolvió {r.status_code}: {r.text}"
    return r.json()


def test_crear_poliza_devuelve_201_y_queda_persistida(cliente):
    creada = _crear(cliente)
    assert creada["numero"] == "POL-IA-00001" and creada["asegurado"] == "Prueba Automática"
    leida = cliente.get(f"/polizas/{creada['id']}")
    assert leida.status_code == 200
    assert leida.json() == creada


@pytest.mark.parametrize("tipo", TIPOS)
@pytest.mark.parametrize("prima", [0.01, 1, 1_250_000.5, 5_000_000])
def test_primas_y_tipos_validos_son_aceptados(cliente, tipo, prima):
    creada = _crear(cliente, tipo=tipo, prima=prima)
    assert (creada["tipo"], creada["prima"]) == (tipo, prima)


@pytest.mark.parametrize("extra", [
    {"prima": 0},
    {"prima": -1},
    {"tipo": "moto"},
    {"asegurado": "ab"},
    {"fecha_inicio": "2026-12-31", "fecha_fin": "2026-01-01"},
    {"siniestros": [{"fecha": "2026-02-01", "monto": -500, "descripcion": "Choque"}]},
], ids=["prima-cero", "prima-negativa", "tipo-invalido", "asegurado-corto",
        "fechas-invertidas", "siniestro-negativo"])
def test_entradas_invalidas_son_rechazadas_y_no_se_guardan(cliente, extra):
    r = cliente.post("/polizas", json=_poliza(**extra))
    assert r.status_code == 422, f"{extra} devolvió {r.status_code}"
    assert cliente.get("/polizas").json() == []


def test_el_asegurado_se_normaliza_y_se_conserva(cliente):
    assert _crear(cliente, asegurado="  prueba   automática ")["asegurado"] == "Prueba Automática"


def test_numero_repetido_da_409(cliente):
    _crear(cliente)
    assert cliente.post("/polizas", json=_poliza()).status_code == 409
    assert len(cliente.get("/polizas").json()) == 1


def test_consultar_poliza_inexistente_da_404(cliente):
    assert cliente.get("/polizas/999999").status_code == 404
    assert cliente.put("/polizas/999999", json={"prima": 10}).status_code == 404
    siniestro = {"fecha": "2026-03-02", "monto": 850_000, "descripcion": "Choque leve"}
    assert cliente.post("/polizas/999999/siniestros", json=siniestro).status_code == 404
    assert cliente.post("/score", json={"numero": "POL-IA-99999"}).status_code == 404


def test_put_parcial_persiste_solo_lo_enviado(cliente):
    creada = _crear(cliente, tipo="hogar")
    r = cliente.put(f"/polizas/{creada['id']}", json={"prima": 999_000})
    assert r.status_code == 200
    esperado = {**creada, "prima": 999_000}
    assert r.json() == esperado
    assert cliente.get(f"/polizas/{creada['id']}").json() == esperado


def test_declarar_siniestro_da_201_y_queda_ligado_a_su_poliza(cliente):
    creada = _crear(cliente)
    siniestro = {"fecha": "2026-03-02", "monto": 850_000, "descripcion": "Choque leve"}
    r = cliente.post(f"/polizas/{creada['id']}/siniestros", json=siniestro)
    assert r.status_code == 201
    assert [s["id"] for s in cliente.get(f"/polizas/{creada['id']}").json()["siniestros"]] == [r.json()["id"]]
    assert [(s["id"], s["numero_poliza"]) for s in cliente.get("/siniestros").json()] == \
        [(r.json()["id"], "POL-IA-00001")]


def test_listar_polizas_devuelve_las_creadas_con_sus_siniestros(cliente):
    siniestro = {"fecha": "2026-03-02", "monto": 850_000, "descripcion": "Choque leve"}
    _crear(cliente, siniestros=[siniestro])
    _crear(cliente, numero="POL-IA-00002")
    r = cliente.get("/polizas")
    assert r.status_code == 200
    assert [(p["numero"], len(p["siniestros"])) for p in r.json()] == [("POL-IA-00001", 1),
                                                                       ("POL-IA-00002", 0)]


def test_resumen_cuenta_y_suma_por_poliza(cliente):
    _crear(cliente, siniestros=[{"fecha": "2026-03-02", "monto": 100, "descripcion": "Uno"},
                                {"fecha": "2026-04-02", "monto": 250.5, "descripcion": "Dos"}])
    r = cliente.get("/resumen")
    assert r.status_code == 200
    assert r.json() == [{"numero": "POL-IA-00001", "n_siniestros": 2, "monto_total": 350.5}]


@pytest.mark.parametrize("tipo", TIPOS)
def test_score_de_poliza_recien_creada_registra_la_prediccion(cliente, tipo):
    _crear(cliente, tipo=tipo)
    r = cliente.post("/score", json={"numero": "POL-IA-00001"})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["numero"] == "POL-IA-00001" and 0.0 <= cuerpo["puntaje"] <= 1.0
    registradas = cliente.get("/predicciones").json()
    assert [(p["numero"], p["alto_riesgo"]) for p in registradas] == [("POL-IA-00001",
                                                                       cuerpo["alto_riesgo"])]
