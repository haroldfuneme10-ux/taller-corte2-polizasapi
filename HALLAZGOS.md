# Hallazgos — Parte A

**Grupo:** <número> · **Integrantes:** Gabriel Aldana, Natalia Carrero, Harold Fúneme

> Cada fila se reprodujo sobre el commit semilla `5a5cc5b` (la etiqueta `v0-semilla` del
> repositorio original), con el servicio recién arrancado (`uvicorn main:app --port 8000`) y la
> `app.db` original. Las salidas son las literales de la terminal.
>
> **Orden de ejecución.** Las filas están ordenadas para poder correrse de arriba abajo sobre UN
> mismo arranque: las que crean pólizas usan un número distinto en cada corrida
> (`POL-Hn-$(date +%s)`), y **H14 va la última a propósito**, porque deja la sesión global
> inservible y, después de ella, cualquier otro comando responde 500. H9 deja un siniestro
> huérfano que hace fallar `GET /siniestros` hasta restaurar la base
> (`git checkout 5a5cc5b -- app.db`).

| ID | Síntoma observable | Causa | Módulo · Sección | SHA donde se observa | Comando de evidencia | Salida obtenida | Corrección aplicada |
|----|--------------------|-------|------------------|----------------------|----------------------|-----------------|---------------------|
| H1 | Un `PUT` que solo envía `prima` borra `tipo`, `asegurado` y `fecha_fin` de la póliza (quedan en `null`) | `actualizar_poliza` hace `setattr` con `datos.model_dump()` sin `exclude_unset=True`: los campos no enviados llegan con su valor por defecto (`None`) y sobrescriben los guardados | M6 · 5. Routing y CRUD | `5a5cc5b` | `curl -s -X PUT localhost:8000/polizas/1 -H "Content-Type: application/json" -d '{"prima":1}' \| grep -o '"tipo":[^,]*'` | `"tipo":null` | `model_dump(exclude_unset=True)`: solo se aplica lo enviado; un `null` explícito da 422 y se valida que la nueva `fecha_fin` siga siendo posterior a `fecha_inicio` |
| H2 | Pedir una póliza que no existe responde **200** con un cuerpo `{"error": ...}` en lugar de 404 (igual en `PUT /polizas/{id}` y en `POST /score`) | Los handlers devuelven un diccionario de error en vez de lanzar `HTTPException`; FastAPI lo serializa como una respuesta exitosa | M6 · 5. Routing y CRUD | `5a5cc5b` | `curl -s -w " [%{http_code}]\n" localhost:8000/polizas/999999` | `{"error":"no existe la póliza 999999"} [200]` | `raise HTTPException(status_code=404)` en GET, PUT, `POST /polizas/{id}/siniestros` y `/score` |
| H3 | Crear una póliza responde **200** en lugar de **201 Created** | `@app.post("/polizas")` no declara `status_code=201`, así que FastAPI usa el 200 por defecto | M6 · 5. Routing y CRUD | `5a5cc5b` | `curl -s -o /dev/null -w "%{http_code}\n" -X POST localhost:8000/polizas -H "Content-Type: application/json" -d '{"numero":"POL-H3-'$(date +%s)'","asegurado":"Ana Rueda","tipo":"auto","prima":1000,"fecha_inicio":"2026-01-15","fecha_fin":"2027-01-14"}'` | `200` | `status_code=201` en `POST /polizas` y en `POST /polizas/{id}/siniestros` |
| H4 | La respuesta de `GET /polizas/{id}` expone `token_firma`, una firma interna derivada del secreto | Ninguna ruta declara `response_model`: `_poliza()` arma el diccionario a mano copiando `token_firma`, y `POST /polizas` devuelve el objeto ORM entero | M6 · 5. Routing y CRUD | `5a5cc5b` | `curl -s localhost:8000/polizas/1 \| grep -c token_firma` | `1` | `response_model=PolizaSalida` (con `from_attributes=True`, sin `token_firma`) en todas las rutas |
| H5 | El nombre del asegurado se guarda siempre como `null`, aunque se envíe uno válido | El `field_validator` `normalizar_asegurado` calcula el nombre normalizado pero no lo devuelve (falta `return`): el validador devuelve `None` y ese es el valor que queda | M7 · 4. Validadores de campo | `5a5cc5b` | `curl -s -X POST localhost:8000/polizas -H "Content-Type: application/json" -d '{"numero":"POL-H5-'$(date +%s)'","asegurado":"  ana   rueda ","tipo":"auto","prima":1250000,"fecha_inicio":"2026-01-15","fecha_fin":"2027-01-14"}' \| grep -o '"asegurado":[^,]*'` | `"asegurado":null` | El validador hace `return " ".join(v.split()).title()`; la columna pasa a `NOT NULL` |
| H6 | Se acepta una póliza cuya `fecha_fin` es anterior a `fecha_inicio` | Cada fecha se valida por separado como `date`; no hay ninguna validación cruzada entre los dos campos | M7 · 5. Modelos anidados y topología jerárquica | `5a5cc5b` | `curl -s -o /dev/null -w "%{http_code}\n" -X POST localhost:8000/polizas -H "Content-Type: application/json" -d '{"numero":"POL-H6-'$(date +%s)'","asegurado":"Luis Perez","tipo":"auto","prima":1000,"fecha_inicio":"2027-01-15","fecha_fin":"2026-01-14"}'` | `200` | `@model_validator(mode="after")` que exige `fecha_fin > fecha_inicio` (422 si no) |
| H7 | Un siniestro anidado con monto negativo y descripción de un carácter se acepta y se guarda | `PolizaEntrada.siniestros` está tipado `list[dict]`: Pydantic no valida el contenido; `SiniestroEntrada` existe pero no se usa ahí | M7 · 5. Modelos anidados y topología jerárquica | `5a5cc5b` | `curl -s -o /dev/null -w "%{http_code}\n" -X POST localhost:8000/polizas -H "Content-Type: application/json" -d '{"numero":"POL-H7-'$(date +%s)'","asegurado":"Ana Rueda","tipo":"auto","prima":1000,"fecha_inicio":"2026-01-15","fecha_fin":"2027-01-14","siniestros":[{"fecha":"2026-02-01","monto":-500,"descripcion":"x"}]}'` | `200` | `siniestros: list[SiniestroEntrada]`, que aplica `Field(gt=0)`, `min_length=3` y el `Literal` de `estado` |
| H8 | `GET /predicciones` no dice a qué póliza pertenece cada predicción: no trae el `numero` (solo el `poliza_id` interno) | El handler arma cada fila a mano con columnas de `Prediccion` y no navega la relación `poliza`; no hay esquema de salida que exija `numero` | M9 · 7. SQLite local e integración con FastAPI | `5a5cc5b` | `curl -s localhost:8000/predicciones \| grep -c '"numero"'` | `0` | `response_model=list[PrediccionSalida]` con `numero` (propiedad que lee `prediccion.poliza.numero`), cargado con `joinedload` |
| H9 | Declarar un siniestro para una póliza inexistente responde 200 y deja un siniestro huérfano; desde ese momento `GET /siniestros` responde 500 | SQLite no hace cumplir las claves foráneas sin `PRAGMA foreign_keys=ON` (no está) y la ruta no comprueba que la póliza exista; luego `_siniestro` falla al leer `s.poliza.numero` de un `None` | M9 · 7. SQLite local e integración con FastAPI | `5a5cc5b` | `curl -s -o /dev/null -X POST localhost:8000/polizas/999999/siniestros -H "Content-Type: application/json" -d '{"fecha":"2026-03-02","monto":850000,"descripcion":"Choque leve"}'; curl -s -o /dev/null -w "%{http_code}\n" localhost:8000/siniestros` | `500` | Listener `connect` que ejecuta `PRAGMA foreign_keys=ON` en cada conexión, y 404 en la ruta si la póliza no existe |
| H10 | La aplicación ignora la variable de entorno `DATABASE_URL`: siempre usa `app.db` | La URL es una constante en `config.py`; no se lee del entorno ni de `.env` | M8 · 3. De lo duro a lo flexible: variables de entorno | `5a5cc5b` | `DATABASE_URL=sqlite:////tmp/otra.db python -c "import database; print(database.engine.url)"` | `sqlite:///app.db` | `Settings(BaseSettings)` lee `DATABASE_URL` del entorno / `.env`; `get_settings()` con `lru_cache`, inyectada con `Depends` |
| H11 | Credenciales (`SECRETO_FIRMA`, `CLAVE_API_REASEGURO`) están versionadas en el repositorio | Las claves están escritas en `config.py` (con un `TODO` que nunca se hizo) y `.gitignore` solo cubre `*.pyc` | M8 · 3. De lo duro a lo flexible: variables de entorno | `5a5cc5b` | `grep -n "rk-polizas" config.py` | `5:CLAVE_API_REASEGURO = "rk-polizas-2026-4b9f0a3d"` | Los secretos salen del código: se leen de `.env` (ignorado por git) y se publica `.env.example` sin valores reales. Las claves filtradas siguen en la historia: hay que rotarlas |
| H12 | La instalación no es reproducible: `requirements.txt` no fija ninguna versión, y `modelo.pkl` se serializó con scikit-learn 1.9.1 | Las ocho dependencias van sin `==`: cada instalación toma la última versión publicada (otra scikit-learn avisa o falla al deserializar el modelo) | M10 · 7. Reproducibilidad sin Docker | `5a5cc5b` | `grep -c "==" requirements.txt` | `0` | Versiones fijadas con `==`, incluida `scikit-learn==1.9.1` (la del modelo) |
| H13 | El contenedor no es alcanzable desde el host con `docker run -p 8000:8000` y reinicia el servidor ante cambios de archivos | El `CMD` enlaza uvicorn a `127.0.0.1` (solo la interfaz interna del contenedor) y usa `--reload`, una opción de desarrollo; además la imagen es `python:latest`, corre como root y copia `app.db` con `COPY . .` | M11 · 6. Estructura de un Dockerfile | `5a5cc5b` | `grep -n CMD Dockerfile` | `8:CMD ["uvicorn", "main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"]` | `Dockerfile` multietapa sobre `python:3.11.9-slim-bookworm`, `CMD` con `--host 0.0.0.0` y sin `--reload`, usuario no root, `HEALTHCHECK` y `.dockerignore` |
| H14 | Un número de póliza repetido devuelve 500 (no 409) y, desde ese momento, **todas** las peticiones responden 500 hasta reiniciar el servicio | `crear_poliza` no trata el `IntegrityError` del `UNIQUE`, y `database.py` comparte UNA sesión global entre todas las peticiones: tras el fallo queda en `PendingRollbackError` y nadie hace `rollback` ni la cierra | M8 · 4. Inyección de dependencias con Depends | `5a5cc5b` | `curl -s -X POST localhost:8000/polizas -H "Content-Type: application/json" -d '{"numero":"POL-2026-00001","asegurado":"Ana Rueda","tipo":"auto","prima":1,"fecha_inicio":"2026-01-15","fecha_fin":"2027-01-14"}' -w "%{http_code} " -o /dev/null; curl -s -o /dev/null -w "%{http_code}\n" localhost:8000/polizas` | `500 500` | `database.get_db` es un generador con `yield` que abre y cierra una sesión por petición (`Depends(get_db)` en cada ruta); se comprueba la unicidad y se captura `IntegrityError` con `rollback` → 409 |

**Defectos vistos que NO van como fila** (para no inflar la tabla; también están corregidos):

- `GET /health` no existe (404). No es un defecto escondido: el enunciado pide crearlo (B10).
- `.gitignore` solo cubre `*.pyc`: `app.db` está versionada (se sacó del índice con `git rm --cached`).
- `create_all` al importar `main.py` en lugar de migraciones (M9 · 6. Modelado de BD y migraciones con Alembic): ahora el esquema lo crea `alembic upgrade head`.
- `tests/test_api.py` escribía en la base real de la aplicación (deja la fila `POL-TEST-00001` en `app.db`) y su segunda corrida falla por número repetido (M10 · 6. Fixtures en pytest).
- `tipo` aceptaba cualquier texto aunque la descripción dice «auto, hogar o vida»: ahora es un `Literal`.
- N+1 en `/polizas`, `/siniestros` y `/resumen` (2001 consultas con 2000 pólizas): se trata en la Parte C.

**Modificación a `contar_consultas.py`:** la columna `estrategia` ya no queda vacía: se copia de
`main.ESTRATEGIA_CARGA`, el diccionario que documenta la estrategia que aplica cada ruta. Nada más
cambia (siembra, conteo y tamaños son los del semilla). Además añadimos `comparar_estrategias.py`,
que mide las estrategias que **no** elegimos (ver Parte C).

---

# Parte C — Interpretación de las consultas

Conteos de `python contar_consultas.py` (10 y 2000 pólizas, 3 siniestros cada una), en
`CONSULTAS.csv`. **Antes de decidir medimos todas las alternativas** con
`python comparar_estrategias.py` (archivo añadido por nosotros): mismo contador
(`before_cursor_execute`), misma siembra y mismos esquemas de salida que la API, de modo que los
*lazy loads* que dispara la serialización también se cuentan. Consultas con 10 / 2000 pólizas;
tiempo con 2000, el mejor de tres, en nuestra máquina y solo orientativo:

| Endpoint | lazy | selectinload | joinedload | agregada | **Elegida** |
|---|---|---|---|---|---|
| `/polizas` | 11 / 2001 · 772 ms | 2 / **5** · 173 ms | 1 / 1 · **209 ms** | — | **selectinload** |
| `/polizas/{id}` | 2 / 2 · 0,6 ms | 2 / 2 · 0,8 ms | 1 / 1 · 0,5 ms | — | **lazy** |
| `/siniestros` | 11 / 2001 · 589 ms | 2 / 5 · 178 ms | 1 / 1 · 99 ms | — | **joinedload** |
| `/resumen` | 11 / 2001 · 570 ms | 2 / 5 · 134 ms | 1 / 1 · 166 ms | 1 / 1 · **7,6 ms** | **agregada** |

Los conteos son deterministas y coinciden con los de `CONSULTAS.csv` para la estrategia elegida;
los tiempos del CSV son algo mayores porque incluyen la petición HTTP completa.

## `/polizas`

**selectinload: 2 consultas con 10 pólizas y 5 con 2000.** La primera trae las pólizas; las
siguientes traen los siniestros con `WHERE siniestros.poliza_id IN (...)`. Lo que nos sorprendió
es que con 2000 no salieron 2 sino 5: SQLAlchemy parte el `IN` en lotes de 500 claves
(`SelectInLoader._chunksize = 500`), así que son 1 + ⌈2000/500⌉ = 5. El número crece por
**lotes de 500**, no por póliza: 400 veces menos que el `lazy` del semilla (1 + 2000 = 2001,
una consulta de siniestros por cada póliza al serializarla: el N+1). La alternativa
«todo de una vez», `joinedload`, sí da **1 consulta**, pero fue **más lenta** (≈209 ms contra
≈173 ms): el `LEFT OUTER JOIN` devuelve una fila por siniestro (6000 filas) repitiendo en cada
una todas las columnas de la póliza, y el ORM tiene que deduplicar (`.unique()`). En una relación
uno-a-muchos, menos consultas no es menos trabajo. Es el caso en que seguir la regla da peor
rendimiento.

## `/polizas/{id}`

**lazy: 2 consultas con 10 y con 2000 pólizas.** `db.get()` trae la póliza por clave primaria
(1) y, al serializar `siniestros`, el `lazy="select"` por defecto lanza una consulta más con
`WHERE poliza_id = ?` (2). El número **no depende del tamaño de la cartera**, porque siempre es
una sola póliza: el N+1 aquí es «1+1». Medimos `selectinload` y da **exactamente lo mismo**
(2 y 2: también es una consulta aparte, solo que con `IN (un id)`). Es el caso en que el código
incumple «cargar todo de una vez» y la medición dice que da igual. `joinedload` ahorra una
consulta (1), pero en una sola fila son décimas de milisegundo y añade un `JOIN` al `db.get`:
dejamos `lazy`, que es el código más simple, porque contar mostró que no hay nada que optimizar.

## `/siniestros`

**joinedload: 1 consulta con 10 y con 2000.** La relación es muchos-a-uno (cada siniestro tiene
UNA póliza), así que el `JOIN` no multiplica filas: 6000 siniestros → 6000 filas, cada una con su
póliza al lado. Con `lazy` el semilla emitía 1 + 2000 = 2001 consultas: no 6001, porque el
*identity map* de la sesión reutiliza la póliza ya cargada para los otros dos siniestros de la
misma póliza; por eso el conteo sigue al número de **pólizas distintas**, no de siniestros.
`selectinload` daría 1 + ⌈2000/500⌉ = 5. Aquí «todo de una vez» sí es lo mejor, y la razón es la
dirección de la relación: es el caso opuesto al de `/polizas`.

## `/resumen`

**agregada: 1 consulta con 10 y con 2000.** Para contar y sumar no hace falta traer ningún
siniestro: `SELECT polizas.numero, count(siniestros.id), coalesce(sum(siniestros.monto), 0) ...
LEFT OUTER JOIN ... GROUP BY polizas.id`. La base devuelve 2000 filas ya resumidas y el ORM no
construye ni un objeto `Siniestro`. Es 1 consulta como `joinedload`, pero ≈7,6 ms contra ≈166 ms:
`joinedload` (y `selectinload`, 5 consultas) materializan 6000 objetos solo para hacer `len()` y
`sum()` en Python. El `LEFT OUTER JOIN` y el `coalesce` hacen que una póliza sin siniestros
aparezca con 0 en vez de desaparecer (hay un test para eso).
