import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

# -------------------------------------------------------
# TEST MODE: set USE_SQLITE=true in .env to use SQLite
# SQLite requires: pip install aiosqlite
# Switch back to USE_SQLITE=false when deploying to EC2
# -------------------------------------------------------
USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"

if USE_SQLITE:
    import sqlite3

    class _SQLiteCursor:
        """Wraps sqlite3 cursor to accept MySQL-style %s placeholders."""
        def __init__(self, cur):
            self._cur = cur

        def execute(self, sql, params=()):
            self._cur.execute(sql.replace("%s", "?"), params)

        def executemany(self, sql, params):
            self._cur.executemany(sql.replace("%s", "?"), params)

        def fetchone(self):
            row = self._cur.fetchone()
            return dict(row) if row else None

        def fetchall(self):
            return [dict(row) for row in self._cur.fetchall()]

        @property
        def lastrowid(self):
            return self._cur.lastrowid

        def close(self):
            self._cur.close()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self._cur.close()

    class _SQLiteConnection:
        """Wraps sqlite3 connection to return _SQLiteCursor and support .cursor() context."""
        def __init__(self, conn):
            self._conn = conn

        def cursor(self):
            return _SQLiteCursor(self._conn.cursor())

        def commit(self):
            self._conn.commit()

        def close(self):
            self._conn.close()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self._conn.close()


def get_connection():
    """
    Returns a DB connection.
    - SQLite: for local testing, no server needed
    - MySQL: for production on RDS
    """
    if USE_SQLITE:
        conn = sqlite3.connect("test.db", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return _SQLiteConnection(conn)
    else:
        return pymysql.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=int(os.getenv("DB_CONNECT_TIMEOUT", "10")),
            read_timeout=int(os.getenv("DB_READ_TIMEOUT", "30")),
            write_timeout=int(os.getenv("DB_WRITE_TIMEOUT", "30")),
        )


