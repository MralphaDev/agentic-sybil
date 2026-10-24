
from app.database.connection import (
    get_connection,
    open_pool,
    close_pool,
)


def test_connection():
    open_pool()

    try:
        with get_connection() as conn:
            result = conn.execute("SELECT version()").fetchone()
            print("Connected to Supabase!")
            print(result[0])  # pyright: ignore[reportOptionalSubscript]
    finally:
        close_pool()


if __name__ == "__main__":
    test_connection()
