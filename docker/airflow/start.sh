#!/bin/bash
set -e

echo "Starting Airflow $1..."
exec airflow "$@"
