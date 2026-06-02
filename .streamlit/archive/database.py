import os
from dotenv import load_dotenv
from libsql_client import create_client

load_dotenv()


def get_client():
    return create_client(
        url=os.getenv("TURSO_DATABASE_URL"),
        auth_token=os.getenv("TURSO_AUTH_TOKEN")
    )
