import psycopg2
import json
from datetime import datetime

with open("data/asia-incidents.json", "r", encoding="utf-8") as f:
    data = json.load(f)

conn = psycopg2.connect(
    host = 'localhost',
    dbname = 'earthquakes',
    user = 'postgres',
    password = '15889'
)

cur = conn.cursor()

for feature in data['features']:
    prop = feature['properties']
    geom = feature['geometry']['coordinates']

    quake_id = feature['id']
    longitude, latitude, depth = geom
    quake_mag = prop['mag']
    sig = prop['sig']
    magtype = prop['magType']
    tsunami = prop['tsunami']
    place = prop['place']

    time = datetime.fromtimestamp(prop['time']/1000.0)

    cur.execute("""
        INSERT INTO earthquakes (id, latitude, time, longitude, depth, mag, magType, tsunami, sig, place)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
    """, (quake_id, latitude, time, longitude, depth, quake_mag, magtype, tsunami, sig, place))

conn.commit()
cur.close()
conn.close()

print('SOOKSES')
