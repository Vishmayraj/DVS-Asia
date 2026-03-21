# DATA INGESTION PIPELINE FOR FIRES FROM FIRMS NASA

import psycopg2
import psycopg2.extras
from psycopg2 import sql
import pandas as pd
from io import StringIO
import time
from datetime import datetime
import os
from dotenv import load_dotenv
import hashlib
import requests
import json
from pathlib import Path

WAIT_TIME = 30
ASIA_COORDS = "25,-10,180,55"

SOURCES = {
    "VIIRS_NOAA20_NRT": "firms_viirs_noaa20_nrt",
    "VIIRS_NOAA21_NRT": "firms_viirs_noaa21_nrt",
    "VIIRS_SNPP_NRT":   "firms_viirs_snpp_nrt",
    "MODIS_NRT":        "firms_modis_nrt",
    "GOES_NRT":         "firms_goes_nrt",
}

COLUMNS = [
    "latitude", "longitude", "bright_ti4", "scan", "track",
    "acq_date", "acq_time", "satellite", "instrument",
    "confidence", "version", "bright_ti5", "frp", "daynight",
]

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)
MAP_KEY = os.getenv("MAP_KEY")

HASHES_PATH = Path(__file__).resolve().parent.parent / "required" / "hashes.json"

HASHES_PATH.parent.mkdir(parents=True, exist_ok=True)

if HASHES_PATH.exists():
    with open(HASHES_PATH, "r") as f:
        last_hashes = json.load(f)
else:
    last_hashes = {}

while True:
    today = datetime.now().date()
    conn = None

    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS")
        )
        cur = conn.cursor()

        for src, table in SOURCES.items():
            url = (
                f"https://firms.modaps.eosdis.nasa.gov/api/area/csv"
                f"/{MAP_KEY}/{src}/{ASIA_COORDS}/1/{today}"
            )

            try:
                response = requests.get(url, timeout=20)
                response.raise_for_status()
                csv_data = response.text

                new_hash = hashlib.md5(csv_data.encode("utf-8")).hexdigest()

                if last_hashes.get(src) == new_hash:
                    print(f"{src}: no change, skipping")
                    continue

                df = pd.read_csv(StringIO(csv_data))

                if df.empty:
                    print(f"{src}: no data for {today}")
                    continue

                missing = [c for c in COLUMNS if c not in df.columns]
                if missing:
                    print(f"{src}: unexpected schema, missing columns {missing}, skipping")
                    continue

                rows = [tuple(row) for row in df[COLUMNS].itertuples(index=False)]

                cur.execute(
                    sql.SQL("TRUNCATE TABLE {}").format(sql.Identifier(table))
                )

                psycopg2.extras.execute_values(
                    cur,
                    sql.SQL("""
                        INSERT INTO {} ({}) VALUES %s
                    """).format(
                        sql.Identifier(table),
                        sql.SQL(", ").join(map(sql.Identifier, COLUMNS))
                    ).as_string(conn),
                    rows
                )

                last_hashes[src] = new_hash
                with open(HASHES_PATH, "w") as f:
                    json.dump(last_hashes, f)

                conn.commit()
                print(f"{src}: refreshed {len(rows)} rows for {today}")

            except requests.exceptions.Timeout:
                print(f"{src}: request timed out, skipping")

            except requests.exceptions.RequestException as e:
                print(f"{src}: network error: {e}, skipping")

            except pd.errors.ParserError as e:
                print(f"{src}: CSV parse error: {e}, skipping")

            except psycopg2.Error as e:
                print(f"{src}: DB error: {e}, rolling back")
                conn.rollback()

            time.sleep(5)

        cur.close()

    except psycopg2.Error as e:
        print(f"DB connection error: {e}")

    except Exception as e:
        print(f"Unexpected error: {e}")

    finally:
        if conn:
            conn.close()

    print(f"Cycle complete, waiting {WAIT_TIME}s...")
    time.sleep(WAIT_TIME)