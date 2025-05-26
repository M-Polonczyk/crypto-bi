FROM apache/airflow:2.8.1-python3.9

USER root
# Install system dependencies if needed for psycopg2 or other Python packages
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#     libpq-dev \
#     && apt-get clean && rm -rf /var/lib/apt/lists/*

USER airflow

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt