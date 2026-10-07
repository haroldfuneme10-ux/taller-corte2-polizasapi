# polizas-api

Servicio de gestión de pólizas de la Aseguradora Santo Tomás. Registra pólizas
y los siniestros que se les declaran, resume la cartera y puntúa el riesgo de
cada póliza con un modelo, guardando cada predicción.

Requiere **Python 3.11** (también probado con 3.13). La imagen de Docker usa
`python:3.11.9-slim-bookworm`.

## Puesta en marcha local (uvicorn)

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env                 # y cambie SECRETO_FIRMA / CLAVE_API_REASEGURO
alembic upgrade head                 # crea el esquema en la base de DATABASE_URL
uvicorn main:app --host 0.0.0.0 --port 8000
```

Compruebe que responde: `curl localhost:8000/health` → `{"estado":"ok","base_datos":"ok"}`.
La documentación interactiva queda en <http://localhost:8000/docs>.

Para desarrollo puede añadir `--reload` a `uvicorn`; **no** en producción ni en el contenedor.

### Configuración

Se lee de variables de entorno o de `.env` (ver `.env.example`; `.env` no se versiona):

| Variable | Por defecto | Qué es |
|---|---|---|
| `DATABASE_URL` | `sqlite:///app.db` | Base de datos (la usan la app **y** Alembic) |
| `SECRETO_FIRMA` | valor de desarrollo | Secreto con que se firma cada póliza |
| `CLAVE_API_REASEGURO` | vacío | Clave del servicio de reaseguro |
| `RUTA_MODELO` | `modelo.pkl` | Modelo serializado (scikit-learn 1.9.1) |
| `UMBRAL_ALTO_RIESGO` | `0.6` | Puntaje a partir del cual `alto_riesgo` es verdadero |

Datos de ejemplo, con el servicio corriendo: `python sembrar_datos.py --polizas 12`.

## En contenedor (Docker)

```bash
docker build -t polizas-api .
docker run -p 8000:8000 polizas-api
curl localhost:8000/health
```

La imagen es multietapa, corre como usuario no root, trae `HEALTHCHECK` y **no** incluye `.env`
ni ninguna base de datos. Al arrancar, `docker-entrypoint.sh` ejecuta `alembic upgrade head` y
luego uvicorn en `0.0.0.0:8000`. La base vive en `/app/datos/polizas.db` dentro del contenedor:

- `docker restart <contenedor>`: los datos **se conservan** (es el mismo sistema de archivos del
  contenedor, que solo se detuvo y volvió a arrancar).
- `docker rm` y un `docker run` nuevo desde la misma imagen: los datos **se pierden** (cada
  contenedor nuevo parte de la imagen, que no trae base). Para conservarlos, monte un volumen:
  `docker run -p 8000:8000 -v polizas-datos:/app/datos polizas-api`.

Para pasar secretos al contenedor: `docker run --env-file .env -e DATABASE_URL=sqlite:////app/datos/polizas.db -p 8000:8000 polizas-api`.

## Endpoints

| Método | Ruta | Respuestas |
|---|---|---|
| POST | `/polizas` | 201 con la póliza creada · 409 número repetido · 422 entrada inválida |
| GET | `/polizas` | 200, cada póliza con sus siniestros |
| GET | `/polizas/{id}` | 200 · 404 |
| PUT | `/polizas/{id}` | 200 · 404 · 422; **parcial**: solo cambia lo enviado |
| POST | `/polizas/{id}/siniestros` | 201 · 404 · 422 |
| GET | `/siniestros` | 200, cada siniestro con el número de su póliza |
| GET | `/resumen` | 200, número de siniestros y monto total por póliza |
| POST | `/score` | 200 con `numero`, `puntaje` y `alto_riesgo` · 404 · 422; registra la predicción |
| GET | `/predicciones` | 200, cada predicción con el `numero` de su póliza |
| GET | `/health` | 200, indica si la base de datos responde |

```bash
curl -X POST localhost:8000/polizas -H "Content-Type: application/json" \
  -d '{"numero": "POL-2026-09001", "asegurado": "Ana Rueda", "tipo": "auto", "prima": 1250000,
       "fecha_inicio": "2026-01-15", "fecha_fin": "2027-01-14"}'
curl -X POST localhost:8000/score -H "Content-Type: application/json" -d '{"numero": "POL-2026-09001"}'
```

## Pruebas

```bash
pytest
```

Corre `tests/` (contrato, pruebas propias y la batería corregida de la Parte D). Cada test usa una
base temporal mediante `app.dependency_overrides[database.get_db]`: la base de la aplicación no
cambia y la batería pasa igual dos veces seguidas.

## Taller (entregables)

- `HALLAZGOS.md` — Parte A (diagnóstico) y Parte C (interpretación de las consultas)
- `CONSULTAS.csv` — Parte C, generado con `python contar_consultas.py`
- `comparar_estrategias.py` — Parte C, conteo de las estrategias alternativas
- `DICTAMEN_IA.md` y `tests/test_ia_corregido.py` — Parte D
- `BITACORA_IA.md` — Parte E · `EQUIPO.md` — integrantes
- `python verificar_entrega.py` — comprueba la forma de la entrega
