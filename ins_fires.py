import pandas as pd
import psycopg2
import time
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()  # loads variables from .env

MAP_KEY = os.getenv("MAP_KEY")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")

# Satellite source → table mapping
sources = {
    "VIIRS_NOAA20_NRT": "firms_viirs_noaa20_nrt",
    "VIIRS_NOAA21_NRT": "firms_viirs_noaa21_nrt",
    "VIIRS_SNPP_NRT": "firms_viirs_snpp_nrt",
    "MODIS_NRT": "firms_modis_nrt",
    "GOES_NRT": "firms_goes_nrt"
}

conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS)
cur = conn.cursor()

while True:
    today = datetime.now().date()
    
    for src, table in sources.items():
        # Asia coordinates (example: bounding box)
        # Format: minLat,minLon,maxLat,maxLon
        asia_coords = "60,5,150,55"  # adjust if needed
        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{src}/{asia_coords}/1/{today}"

        try:
            df = pd.read_csv(url)
            constraint_name = table.replace("firms_", "").replace("_nrt", "") + "_unique"
            print(f"Inserting into {table} using constraint: {constraint_name}")
            
            for _, row in df.iterrows():
                cur.execute(f"""
                    INSERT INTO {table} (latitude, longitude, bright_ti4, scan, track,
                                         acq_date, acq_time, satellite, instrument,
                                         confidence, version, bright_ti5, frp, daynight)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT ON CONSTRAINT {constraint_name} DO NOTHING;
                """, tuple(row.values))


            conn.commit()
            print(f"{src}: Inserted {len(df)} rows for {today}")

        except Exception as e:
            print(f"Failed {src} for {today}: {e}")

        time.sleep(0.25)  # short pause between satellites

    # wait 2–3 seconds before next full round
    time.sleep(2.5)
