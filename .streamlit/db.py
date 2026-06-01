import os
from sqlalchemy import create_engine

def get_engine():
    url = (
        f"postgresql+psycopg2://{os.getenv('PGUSER')}:"
        f"{os.getenv('PGPASSWORD')}@{os.getenv('PGHOST')}:"
        f"{os.getenv('PGPORT', 5432)}/{os.getenv('PGDATABASE')}"
    )
    return create_engine(url)