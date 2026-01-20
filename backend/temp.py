import psycopg2
from psycopg2 import sql
import csv
from dotenv import load_dotenv
import os
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

conn = psycopg2.connect(
    dbname = os.getenv("DB_NAME"), 
    user = os.getenv("DB_USER"), 
    password = os.getenv("DB_PASS")
)
cur = conn.cursor()

tables = [
    "earthquakes",
    "firms_viirs_noaa20_nrt",
    "firms_viirs_noaa21_nrt",
    "firms_viirs_snpp_nrt",
    "firms_modis_nrt",
    "firms_goes_nrt",
    "gdacs_live"
]

for table in tables:
    cur.execute(sql.SQL("SELECT * FROM {}").format(sql.Identifier(table)))
    rows = cur.fetchall()
    colnames = [desc[0] for desc in cur.description]

    with open(f"temp/{table}.csv", "w", newline="", encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(colnames)
        writer.writerows(rows)

    print(f"Export of {table}.csv DONE")

cur.close()
conn.close()
print("SOOKSES")