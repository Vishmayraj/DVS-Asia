# THIS IS ONLY TO BE RUN AT THE END OF EACH YEAR

import psycopg2
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS")
)
cur = conn.cursor()

cur.execute("SELECT MAX(time) FROM earthquakes")
last_time = cur.fetchone()[0]

if last_time:
    last_year = last_time.year
else:
    last_year = datetime.now(timezone.utc).year

current_year = datetime.now(timezone.utc).year

if current_year > last_year:
    print(f"Year change detected: {last_year} -> {current_year}")

    cur.execute("""
        INSERT INTO earthquakes_archive
        SELECT * FROM earthquakes
    """)

    cur.execute("""
        DELETE FROM earthquakes
        WHERE time < NOW() - INTERVAL '30 days'
    """)

    conn.commit()
    print(f"✅ Archived {last_year} earthquakes and reset table for {current_year}")
else:
    print("No year change detected. No action taken.")

cur.close()
conn.close()
