 # Shared connection pool —> imported by all routers

import psycopg2.pool
import os
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", 6543)),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS"),
)