#!/bin/bash
set -e

if [[ -z "$AIRFLOW__DATABASE__SQL_ALCHEMY_CONN" ]]; then
  echo "ERROR: AIRFLOW__DATABASE__SQL_ALCHEMY_CONN is not set"
  exit 1
fi

# airflow db migrate

exec "$@"
