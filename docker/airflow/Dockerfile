FROM apache/airflow:3.0.2-python3.12

# Install system dependencies if needed for psycopg2 or other Python packages
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#     libpq-dev \
#     && apt-get clean && rm -rf /var/lib/apt/lists/*

USER airflow
# Not necessary to set the working directory as Airflow's Docker image already sets it to /opt/airflow
# WORKDIR /opt/airflow

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt \
  && rm requirements.txt

COPY ./docker/airflow/entrypoint.sh /entrypoint.sh
# COPY ./docker/airflow/start.sh /start.sh

# ENTRYPOINT ["/entrypoint.sh"]
