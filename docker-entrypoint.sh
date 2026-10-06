#!/bin/sh
# Crea o actualiza el esquema de la base (idempotente) y cede el proceso al CMD.
set -e
alembic upgrade head
exec "$@"
