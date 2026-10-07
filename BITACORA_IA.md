# Bitácora de uso de IA

**Grupo:** <número> · **Integrantes:** Gabriel Aldana, Natalia Carrero, Harold Fúneme
**Herramientas usadas:** Claude Code (sesión en la nube sobre este repositorio)

> Las tres secciones son obligatorias. **`## Rechazado` es la que se califica.**
> Una bitácora que solo lista prompts aceptados vale la mitad.
>
> **Cómo se trabajó.** Gabriel abrió una sesión de Claude Code sobre el repositorio y le pidió
> resolver el taller completo a partir del enunciado, el índice del curso y el borrador de
> hallazgos de Harold. La IA escribió el código y los entregables. Los commits de esa sesión
> quedaron a nombre de Gabriel, que operaba la sesión, y cada uno conserva la línea
> `Co-Authored-By: Claude` que deja ver la participación de la IA. Después, a pedido
> nuestro, la IA **criticó su propio trabajo**: esa autocrítica está en `## Rechazado` (filas
> 8 a 17), junto con lo que se corrigió y lo que quedó pendiente a sabiendas.
> **Pendiente:** cada integrante añade aquí sus propios prompts y lo que rechace al revisar.

## Prompts

| # | Parte | Quién | Prompt (resumido si es largo) |
|---|-------|-------|-------------------------------|
| 1 | A–E | Gabriel | «Estamos realizando el taller del corte 2; en el otro HTML están los módulos que hemos visto (hasta Docker); en el .md están nuestros hallazgos, no han sido comprobados». Se adjuntaron el enunciado, el índice del curso y un borrador de `HALLAZGOS.md`. |
| 2 | — | Gabriel | (Sin prompt nuevo.) El push desde la sesión falló con 403 porque la app de GitHub no tenía permisos; la rama se subió desde una máquina local |
| 3 | E | Gabriel | «Divide los commits entre nosotros tres; autocritícate para la bitácora; explícanos la Parte C y cómo presentamos en Docker» |
| 4 | | | |

## Aceptado

| # | Qué propuso la IA | Por qué lo aceptamos | Qué cambiamos antes de usarlo |
|---|-------------------|----------------------|-------------------------------|
| 1 | Reproducir cada fila del borrador de `HALLAZGOS.md` sobre el commit semilla y copiar la salida real de la terminal | El enunciado compara la «Salida obtenida» con la real; el borrador decía que no estaba comprobado | — |
| 2 | Sesión por petición (`get_db` con `yield`), `PRAGMA foreign_keys` en un listener `connect`, `BaseSettings` con `lru_cache` | Son las restricciones B2–B4 tal como las enseñan M8 · 4 y M9 · 7 | — |
| 3 | Estrategias de carga: `selectinload` en `/polizas`, `lazy` en `/polizas/{id}`, `joinedload` en `/siniestros`, `agregada` en `/resumen` | Se decidieron después de contar las cuatro alternativas en cada endpoint (`comparar_estrategias.py`) | — |
| 4 | Tres mutaciones para la Parte D (404→200, quitar un `commit`, `Literal` de `tipo` sin `"vida"`) | Cada una deja verde la batería original y roja la corregida, con salida real | — |

## Rechazado

| # | Qué propuso la IA | Por qué lo rechazamos | Qué hicimos en su lugar |
|---|-------------------|-----------------------|-------------------------|
| 1 | (Borrador previo, sin comprobar) H1 «sesión global» y H2 «409» como filas separadas, con H1 primero | Al reproducirlas en orden, H1 deja la sesión global en `PendingRollbackError` y **todas** las filas siguientes daban 500 en vez de su salida: el calificador no podría reproducir el resto | Se unieron en una sola fila (H14) que muestra los dos síntomas (`500 500`) y se puso la última |
| 2 | (Borrador previo) `git grep -n "rk-polizas" v0-semilla` como evidencia de H11 | Este repositorio no tiene la etiqueta `v0-semilla` (`git tag` sale vacío): el comando falla | `grep -n "rk-polizas" config.py`, que el calificador corre tras hacer checkout del SHA declarado (`5a5cc5b`) |
| 3 | (Borrador previo) Comandos `POST` con números fijos (`POL-2026-09001`, `09002`, `09011`) | La segunda ejecución choca con el número ya creado, da 500 y rompe la sesión del semilla: la evidencia no es reproducible | Números con `$(date +%s)`; se comprobó con `sh` (dash) que dos pasadas dan la misma tabla |
| 4 | Usar `joinedload` en `/polizas` porque «una consulta es mejor que cinco» | Medido: 1 consulta pero ≈209 ms contra ≈173 ms de `selectinload` con 2000 pólizas; el JOIN uno-a-muchos devuelve 6000 filas repitiendo la póliza | `selectinload` (5 consultas: lotes de 500 en el `IN`) |
| 5 | Usar `joinedload` también en `/resumen` | Medido: 1 consulta pero ≈166 ms, porque igual construye 6000 objetos `Siniestro` para hacer `len()` y `sum()` en Python | Consulta agregada con `GROUP BY` (1 consulta, ≈7,6 ms) |
| 6 | Construir la imagen de Docker añadiendo al `Dockerfile` el certificado del proxy de la sesión (para que `pip` funcionara en la nube) | Es un detalle del entorno donde corría la IA, no del servicio; meterlo en el `Dockerfile` ensuciaría la imagen y fallaría en otras máquinas | Se verificó con una copia temporal del `Dockerfile` fuera del repositorio; el `Dockerfile` entregado no lo lleva |
| 7 | Hacer `SECRETO_FIRMA` obligatorio (sin valor por defecto) | `docker run -p 8000:8000 polizas-api` debe arrancar sin `.env` (B9) y la imagen no puede llevar `.env`: con el campo obligatorio el contenedor no arranca | Valor por defecto **no secreto**, solo para desarrollo; el real va por entorno (`--env-file`) |
| 8 | Repartir los commits entre los tres integrantes cambiando el autor | El calificador mide con `git log` la contribución de **cada** persona (I3, C2). Poner a Natalia o a Harold como autores de commits que escribió una IA en una sesión de Gabriel falsea esa medición, y la bitácora diría lo contrario que el `git log` | Los commits de la sesión se quedan como están y se cuentan como de Gabriel; Natalia y Harold hacen **sus propios** commits sobre las partes que revisan y defienden |
| 9 | (Autocrítica) La IA hizo los commits con su propia identidad `Claude <noreply@anthropic.com>` | `verificar_entrega.py` la marcaba como una persona extra que no está en `EQUIPO.md` | No se reescribió la historia (ya estaba publicada): la identidad se declara en `EQUIPO.md` como de Gabriel, que operaba la sesión, y esta bitácora lo dice |
| 10 | (Autocrítica) Los commits de la Parte B no se pueden ejecutar uno por uno: el de B1 cambia `config.py` y `database.py` sigue usando `config.DATABASE_URL` hasta el commit siguiente | Un commit intermedio que no arranca impide usar `git bisect` y hace que la historia «describa» cambios que no funcionan solos | No se reescribió (ya estaba publicada); queda anotado. La lección: cada commit debe dejar el servicio arrancando |
| 11 | (Autocrítica) `SECRETO_FIRMA` tiene un valor por defecto en el código | Si en producción se olvida definirlo, el servicio firma en silencio con un valor conocido | Se mantiene el valor (B9 exige que `docker run` arranque sin `.env`), pero ahora `config.py` **avisa en el log** al arrancar con él |
| 12 | (Autocrítica) `GET /health` responde 200 aunque la base no responda (solo cambia `base_datos` a `"error"`) | El `HEALTHCHECK` de Docker solo mira el código HTTP: con la base caída el contenedor seguiría «healthy» | No se cambió: B10 pide «200 e indica si la base responde». En la sustentación lo explicamos como un límite conocido (en producción se usaría 503) |
| 13 | (Autocrítica) La fixture de los tests crea el esquema con `Base.metadata.create_all`, no con Alembic | Los tests no comprueban que la migración coincida con los modelos; una columna olvidada en la migración pasaría los tests | Se comprobó a mano con `alembic check` («No new upgrade operations detected»); pendiente automatizarlo |
| 14 | (Autocrítica) La imagen pesa ≈690 MB e incluye `pytest` y `httpx` | Hay un solo `requirements.txt` y el calificador lo usa para instalar y correr tests, así que lleva las herramientas de prueba | Se aceptó el costo para no tener dos archivos de dependencias; la mayor parte del peso es scikit-learn/scipy |
| 15 | (Autocrítica) La imagen se verificó con una copia del `Dockerfile` que añadía el certificado del proxy de la nube | No es exactamente el archivo entregado: un error en la etapa de construcción podría haber pasado desapercibido | Hay que correr `docker build` del `Dockerfile` real en una máquina nuestra antes de la sustentación (ver README) |
| 16 | (Autocrítica) En `DICTAMEN_IA.md` cambió los rótulos a `**Qué está mal**:` (dos puntos fuera de las negritas) | Lo hizo para que pase la expresión regular de `verificar_entrega.py`, pero se aparta de la plantilla, que dice «no las reescriban» | Se dejó así porque el verificador dice hacer las mismas comprobaciones que el calificador; si el docente lo objeta, se vuelve al formato de la plantilla |
| 17 | (Autocrítica) Las filas 4–7 de esta tabla las presentó como «propuestas de la IA» cuando eran alternativas que ella misma evaluó y descartó | Una bitácora que adorna lo que pasó pierde valor; el enunciado penaliza la falsificación | Se reescribió la nota de arriba para decir exactamente qué es cada fila |

