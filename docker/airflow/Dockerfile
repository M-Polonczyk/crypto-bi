FROM apache/airflow:slim-3.0.2rc1-python3.9

# Install system dependencies if needed for psycopg2 or other Python packages
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#     libpq-dev \
#     && apt-get clean && rm -rf /var/lib/apt/lists/*

USER airflow

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
  && rm requirements.txt

COPY ./docker/airflow/entrypoint.sh /entrypoint.sh
# COPY ./docker/airflow/start.sh /start.sh

# ENTRYPOINT ["/entrypoint.sh"]
