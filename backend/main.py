from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import os
from dotenv import load_dotenv
from pathlib import Path

app = FastAPI()

# CORS: allow frontend on GitHub Pages or Netlify
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # can restrict later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
DB_NAME=os.getenv("DB_NAME")
DB_USER=os.getenv("DB_USER")
DB_PASS=os.getenv("DB_PASS")


@app.get("/")
def root():
    return {"status": "DVS backend is live!", "name": DB_NAME, "user": DB_USER, "pass" : DB_PASS}

@app.get("/earthquakes")
def get_earthquakes():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

    cur = conn.cursor()
    cur.execute("""
        SELECT id, latitude, longitude, mag, place, time
        FROM earthquakes
        ORDER BY time DESC
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [
        {"id": r[0], "lat": r[1], "lng": r[2],
         "mag": r[3], "place": r[4], "time": r[5].isoformat()}
        for r in rows
    ]

@app.get("/firms_fires/goes")
def get_fires():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

    cur = conn.cursor()
    cur.execute("""
        SELECT id, latitude, longitude, confidence
        FROM firms_goes_nrt
    """)

    rows = cur.fetchall()
    cur.close(); conn.close()
    return [
        {"id": r[0], "latitude": r[1], "longitude": r[2], "confidence": r[3]}
        for r in rows
    ]

@app.get("/firms_fires/modis")
def get_fires():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

    cur = conn.cursor()
    cur.execute("""
        SELECT id, latitude, longitude, confidence
        FROM firms_modis_nrt
    """)

    rows = cur.fetchall()
    cur.close(); conn.close()
    return [
        {"id": r[0], "latitude": r[1], "longitude": r[2], "confidence": r[3]}
        for r in rows
    ]

@app.get("/firms_fires/noaa20")
def get_fires():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

    cur = conn.cursor()
    cur.execute("""
        SELECT id, latitude, longitude, confidence
        FROM firms_viirs_noaa20_nrt
    """)

    rows = cur.fetchall()
    cur.close(); conn.close()
    return [
        {"id": r[0], "latitude": r[1], "longitude": r[2], "confidence": r[3]}
        for r in rows
    ]

@app.get("/firms_fires/noaa21")
def get_fires():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

    cur = conn.cursor()
    cur.execute("""
        SELECT id, latitude, longitude, confidence
        FROM firms_viirs_noaa21_nrt
    """)

    rows = cur.fetchall()
    cur.close(); conn.close()
    return [
        {"id": r[0], "latitude": r[1], "longitude": r[2], "confidence": r[3]}
        for r in rows
    ]

@app.get("/firms_fires/snpp")
def get_fires():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

    cur = conn.cursor()
    cur.execute("""
        SELECT id, latitude, longitude, confidence
        FROM firms_viirs_snpp_nrt
    """)

    rows = cur.fetchall()
    cur.close(); conn.close()
    return [
        {"id": r[0], "latitude": r[1], "longitude": r[2], "confidence": r[3]}
        for r in rows
    ]

