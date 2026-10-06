"""Pruebas propias del servicio. Aisladas: usan la fixture `cliente` de conftest.py.

    pytest
"""
POLIZA = {
    "numero": "POL-2026-00001",
    "asegurado": "Ana Rueda",
    "tipo": "auto",
    "prima": 1_000_000,
    "fecha_inicio": "2026-01-01",
    "fecha_fin": "2026-12-31",
}
SINIESTRO = {"fecha": "2026-03-02", "monto": 850_000, "descripcion": "Choque leve"}


def _crear(cliente, **extra):
    r = cliente.post("/polizas", json={**POLIZA, **extra})
    assert r.status_code == 201, r.text
    return r.json()


def test_health_indica_que_la_base_responde(cliente):
    r = cliente.get("/health")
    assert r.status_code == 200
    assert r.json() == {"estado": "ok", "base_datos": "ok"}


def test_crear_y_leer_de_vuelta(cliente):
    creada = _crear(cliente, siniestros=[SINIESTRO])
    leida = cliente.get(f"/polizas/{creada['id']}")
    assert leida.status_code == 200
    assert leida.json() == creada
    assert [s["monto"] for s in leida.json()["siniestros"]] == [850_000]


def test_listar_incluye_siniestros_y_no_filtra_token(cliente):
    _crear(cliente, siniestros=[SINIESTRO, SINIESTRO])
    polizas = cliente.get("/polizas").json()
    assert len(polizas) == 1 and len(polizas[0]["siniestros"]) == 2
    assert "token_firma" not in polizas[0]


def test_asegurado_se_normaliza(cliente):
    assert _crear(cliente, asegurado="  ana   rueda ")["asegurado"] == "Ana Rueda"


def test_numero_duplicado_da_409_y_no_rompe_el_servicio(cliente):
    _crear(cliente)
    assert cliente.post("/polizas", json=POLIZA).status_code == 409
    assert cliente.get("/polizas").status_code == 200
    assert len(cliente.get("/polizas").json()) == 1


def test_entradas_invalidas_dan_422(cliente):
    invalidas = [
        {"prima": 0},
        {"prima": -5},
        {"tipo": "moto"},
        {"asegurado": "ab"},
        {"fecha_inicio": "2026-12-31", "fecha_fin": "2026-01-01"},
        {"fecha_fin": "2026-01-01"},  # igual a fecha_inicio: tampoco es posterior
        {"siniestros": [{**SINIESTRO, "monto": -1}]},
        {"siniestros": [{"fecha": "no-es-fecha", "monto": 1, "descripcion": "abc"}]},
    ]
    for extra in invalidas:
        r = cliente.post("/polizas", json={**POLIZA, **extra})
        assert r.status_code == 422, f"{extra} devolvió {r.status_code}"
    assert cliente.get("/polizas").json() == []


def test_put_parcial_solo_cambia_lo_enviado(cliente):
    creada = _crear(cliente, tipo="hogar")
    r = cliente.put(f"/polizas/{creada['id']}", json={"prima": 2_000_000})
    assert r.status_code == 200
    assert r.json() == {**creada, "prima": 2_000_000}


def test_put_rechaza_null_y_fechas_incoherentes(cliente):
    creada = _crear(cliente)
    assert cliente.put(f"/polizas/{creada['id']}", json={"tipo": None}).status_code == 422
    assert cliente.put(f"/polizas/{creada['id']}", json={"fecha_fin": "2025-06-01"}).status_code == 422
    assert cliente.get(f"/polizas/{creada['id']}").json() == creada


def test_inexistente_da_404(cliente):
    assert cliente.get("/polizas/999").status_code == 404
    assert cliente.put("/polizas/999", json={"prima": 1}).status_code == 404
    assert cliente.post("/polizas/999/siniestros", json=SINIESTRO).status_code == 404
    assert cliente.post("/score", json={"numero": "POL-0000-00000"}).status_code == 404
    assert cliente.get("/siniestros").json() == []  # no quedó ningún siniestro huérfano


def test_declarar_siniestro_y_listarlo_con_su_poliza(cliente):
    creada = _crear(cliente)
    r = cliente.post(f"/polizas/{creada['id']}/siniestros", json=SINIESTRO)
    assert r.status_code == 201
    siniestros = cliente.get("/siniestros").json()
    assert [(s["id"], s["numero_poliza"]) for s in siniestros] == [(r.json()["id"], POLIZA["numero"])]


def test_resumen_cuenta_y_suma_por_poliza(cliente):
    _crear(cliente, siniestros=[{**SINIESTRO, "monto": 100.5}, {**SINIESTRO, "monto": 200.25}])
    _crear(cliente, numero="POL-2026-00002")  # sin siniestros: debe salir con 0, no desaparecer
    assert cliente.get("/resumen").json() == [
        {"numero": "POL-2026-00001", "n_siniestros": 2, "monto_total": 300.75},
        {"numero": "POL-2026-00002", "n_siniestros": 0, "monto_total": 0.0},
    ]


def test_score_registra_la_prediccion(cliente):
    _crear(cliente)
    r = cliente.post("/score", json={"numero": POLIZA["numero"]})
    assert r.status_code == 200
    cuerpo = r.json()
    assert set(cuerpo) == {"numero", "puntaje", "alto_riesgo"} and 0 <= cuerpo["puntaje"] <= 1
    predicciones = cliente.get("/predicciones").json()
    assert len(predicciones) == 1
    assert predicciones[0]["numero"] == POLIZA["numero"]
    assert predicciones[0]["alto_riesgo"] == cuerpo["alto_riesgo"]
