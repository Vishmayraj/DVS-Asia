# DATA INGESTION PIPELINE FOR FIRES FROM FIRMS NASA

import pandas as pd
import psycopg2
from io import StringIO
import time
from datetime import datetime
import os
from dotenv import load_dotenv
import hashlib
import requests
import json
from pathlib import Path

batchwaittime = 30

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)
MAP_KEY = os.getenv("MAP_KEY")

sources = {
    "VIIRS_NOAA20_NRT": "firms_viirs_noaa20_nrt",
    "VIIRS_NOAA21_NRT": "firms_viirs_noaa21_nrt",
    "VIIRS_SNPP_NRT": "firms_viirs_snpp_nrt",
    "MODIS_NRT": "firms_modis_nrt",
    "GOES_NRT": "firms_goes_nrt"
}

conn = psycopg2.connect(
    host = os.getenv("DB_HOST"),
    dbname = os.getenv("DB_NAME"), 
    user = os.getenv("DB_USER"), 
    password = os.getenv("DB_PASS")
)
cur = conn.cursor()

# store last hashes in memory
if os.path.exists("required/hashes.json"):
    with open("required/hashes.json", "r") as f:
        last_hashes = json.load(f)
else:
    last_hashes = {}

while True:
    today = datetime.now().date()
    
    for src, table in sources.items():
        asia_coords = "60,5,150,55"
        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{src}/{asia_coords}/1/{today}"

        try:
            # get raw CSV content as text
            response = requests.get(url)
            response.raise_for_status()
            csv_data = response.text

            # compute a quick hash fingerprint
            new_hash = hashlib.md5(csv_data.encode('utf-8')).hexdigest()

            # if hash unchanged, skip this satellite
            if last_hashes.get(src) == new_hash:
                print(f"{src}: No change detected, skipping update.")
                continue

            # hash changed → new data
            last_hashes[src] = new_hash
            with open("required/hashes.json", "w") as f:
                json.dump(last_hashes, f)
            print(f"{src}: New data detected, refreshing table...")

            # parse and truncate before insert
            df = pd.read_csv(StringIO(csv_data))
            cur.execute(f"TRUNCATE TABLE {table};")

            for _, row in df.iterrows():
                cur.execute(f"""
                    INSERT INTO {table} (latitude, longitude, bright_ti4, scan, track,
                                         acq_date, acq_time, satellite, instrument,
                                         confidence, version, bright_ti5, frp, daynight)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);
                """, tuple(row.values))

            conn.commit()
            print(f"{src}: Table refreshed with {len(df)} rows for {today}")

        except Exception as e:
            print(f"Failed {src} for {today}: {e}")

        time.sleep(5)

    print(f'Waiting for {batchwaittime}s..')
    time.sleep(batchwaittime)

cur.close()
conn.close()
