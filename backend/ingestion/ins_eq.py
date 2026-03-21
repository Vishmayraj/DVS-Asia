# INGESTION PIPELINE FOR EARTHQUAKES FROM USGS

import psycopg2
import requests
import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
import time
from pathlib import Path

WAIT_TIME = 30
RUN_ONCE = "--once" in sys.argv
USGS_URL = (
    "https://earthquake.usgs.gov/fdsnws/event/1/query"
    "?format=geojson"
    "&minlatitude=-10&maxlatitude=80"
    "&minlongitude=25&maxlongitude=170"
)

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(env_path)

while True:
    conn = None
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", 5432)),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS")
        )
        cur = conn.cursor()

        response = requests.get(USGS_URL, timeout=15)
        response.raise_for_status()
        data = response.json()

        inserted = 0
        updated = 0

        for feature in data["features"]:
            prop = feature["properties"]
            geom = feature["geometry"]["coordinates"]

            quake_id = feature["id"]
            longitude, latitude, depth = geom
            mag = prop.get("mag")
            sig = prop.get("sig")
            magtype = prop.get("magType")
            tsunami = prop.get("tsunami", 0)
            place = prop.get("place", "Unknown")
            quake_time = datetime.fromtimestamp(prop["time"] / 1000.0, tz=timezone.utc)

            cur.execute("""
                INSERT INTO earthquakes
                    (id, latitude, time, longitude, depth, mag, magtype, tsunami, sig, place)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                    SET mag     = EXCLUDED.mag,
                        place   = EXCLUDED.place,
                        sig     = EXCLUDED.sig,
                        magtype = EXCLUDED.magtype
                    WHERE earthquakes.mag IS DISTINCT FROM EXCLUDED.mag
                       OR earthquakes.place IS DISTINCT FROM EXCLUDED.place
            """, (quake_id, latitude, quake_time, longitude, depth, mag, magtype, tsunami, sig, place))

            if cur.rowcount == 1:
                if cur.statusmessage.startswith("UPDATE"):
                    updated += 1
                else:
                    inserted += 1

        cur.execute("""
            INSERT INTO earthquakes_archive
            SELECT * FROM earthquakes
            WHERE time < NOW() - INTERVAL '30 days'
            ON CONFLICT (id) DO NOTHING
        """)
        archived = cur.rowcount

        cur.execute("""
            DELETE FROM earthquakes
            WHERE time < NOW() - INTERVAL '30 days'
        """)
        purged = cur.rowcount

        conn.commit()
        cur.close()

        print(f"inserted={inserted} updated={updated} archived={archived} purged={purged} | {'done.' if RUN_ONCE else f'waiting {WAIT_TIME}s...'}")

    except requests.exceptions.Timeout:
        print("USGS request timed out, retrying...")

    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")

    except psycopg2.Error as e:
        print(f"DB error: {e}")

    except Exception as e:
        print(f"Unexpected error: {e}")

    finally:
        if conn:
            conn.close()

    if RUN_ONCE:
        break
    time.sleep(WAIT_TIME)