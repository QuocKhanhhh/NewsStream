FROM apache/airflow:2.10.3-python3.11

COPY requirements-runtime.txt /requirements-runtime.txt
RUN pip install --no-cache-dir -r /requirements-runtime.txt

ENV PYTHONPATH=/opt/airflow:/opt/airflow/src:/opt/airflow/dags
