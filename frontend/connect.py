import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

conn = psycopg2.connect(
    host="db.pzvjnazsaztccmlcxxpu.supabase.co",
    port=5432,
    dbname="postgres",
    user="postgres",
    password="Vishmayraj15889*",
    sslmode="require"
)
cur = conn.cursor()

cur.execute("")
conn.commit()
cur.close()
conn.close()