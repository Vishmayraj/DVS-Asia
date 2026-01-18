# INGESTION PIPELINE FOR EARTHQUAKES FROM USGS

import psycopg2
import requests
import os
from datetime import datetime
from dotenv import load_dotenv
import time

wait_time = 30

#getting db metadata from .env
load_dotenv()
conn = psycopg2.connect(
    dbname = os.getenv("DB_NAME"),
    user = os.getenv("DB_USER"),
    password = os.getenv("DB_PASS")
)
cur = conn.cursor()

while True:
    try:
        #implementing live data retrieval logic
        url = "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&minlatitude=-10&maxlatitude=80&minlongitude=25&maxlongitude=170"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        for feature in data['features']:
            prop = feature['properties']
            geom = feature['geometry']['coordinates']

            quake_id = feature['id']
            longitude, latitude, depth = geom
            quake_mag = prop.get('mag')
            sig = prop.get('sig')
            magtype = prop.get('magType')
            tsunami = prop.get('tsunami', 0)
            place = prop.get('place', 'Unknown')

            quake_time = datetime.fromtimestamp(prop['time']/1000.0)

            cur.execute("""
                INSERT INTO earthquakes (id, latitude, time, longitude, depth, mag, magtype, tsunami, sig, place)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (quake_id, latitude, quake_time, longitude, depth, quake_mag, magtype, tsunami, sig, place))

        conn.commit()
        
        print(f"Success, waiting for {wait_time}s...")
        time.sleep(wait_time)

    except Exception as e:
        print('Error: ', e)
        time.sleep(wait_time)

cur.close()
conn.close()