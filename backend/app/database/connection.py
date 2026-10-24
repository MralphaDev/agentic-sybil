import os
from pathlib import Path

from dotenv import load_dotenv
from psycopg_pool import ConnectionPool

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ENV_PATH, override=True)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Missing DATABASE_URL")

pool = ConnectionPool(
    conninfo=DATABASE_URL,
    min_size=1,
    max_size=10,
    open=False,
)


def open_pool() -> None:
    if pool.closed:
        pool.open(wait=True)


def close_pool() -> None:
    if not pool.closed:
        pool.close()


def get_connection():
    """Borrow a connection; return it to the pool when the context exits."""
    return pool.connection()
