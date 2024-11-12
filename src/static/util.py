from pathlib import Path
import os
import dotenv
import sqlalchemy
from crewai.telemetry import Telemetry

dotenv.load_dotenv()

DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_USER = os.environ["DB_USER"]
DB_ENDPOINT = os.environ["DB_ENDPOINT"]
DB_PORT = os.environ["DB_PORT"]

__db_url = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_ENDPOINT}:{DB_PORT}/postgres'
ENGINE = sqlalchemy.create_engine(__db_url)

PROJECT_ROOT = Path(__file__).parent.parent


# Disable CrewAI Telemetry
def noop(*args, **kwargs):
    pass


for attr in dir(Telemetry):
    if callable(getattr(Telemetry, attr)) and not attr.startswith("__"):
        setattr(Telemetry, attr, noop)