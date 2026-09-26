import sys
from pathlib import Path


AIRFLOW_DIR = Path(__file__).resolve().parents[1]
if str(AIRFLOW_DIR) not in sys.path:
    sys.path.insert(0, str(AIRFLOW_DIR))
