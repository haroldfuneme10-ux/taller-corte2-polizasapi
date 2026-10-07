# Bitácora de uso de IA

**Grupo:** <número> · **Integrantes:** Harold <apellido>, <nombre 2>, <nombre 3>
**Herramientas usadas:** Claude Code (sesión en la nube sobre este repositorio)

> Las tres secciones son obligatorias. **`## Rechazado` es la que se califica.**
> Una bitácora que solo lista prompts aceptados vale la mitad.
>
> **Pendiente del grupo antes de entregar:** completar la columna «Quién», añadir los prompts
> que hayan usado fuera de esta sesión y, sobre todo, registrar en `## Rechazado` lo que
> ustedes decidan no aceptar al revisar este trabajo. Lo que hay abajo describe, sin adornos,
> lo que pasó en la sesión con Claude Code: las filas 1–3 de `## Rechazado` son correcciones al
> borrador de `HALLAZGOS.md` que se trajo a la sesión (déjenlas solo si ese borrador salió de una
> IA); las filas 4–7 son alternativas que se evaluaron en la sesión y se descartaron con el
> argumento indicado.

## Prompts

| # | Parte | Quién | Prompt (resumido si es largo) |
|---|-------|-------|-------------------------------|
| 1 | A–E | Harold | «Estamos realizando el taller del corte 2; en el otro HTML están los módulos que hemos visto (hasta Docker); en el .md están nuestros hallazgos, no han sido comprobados». Se adjuntaron el enunciado, el índice del curso y un borrador de `HALLAZGOS.md`. |
| 2 | | | |

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
