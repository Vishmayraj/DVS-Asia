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

# Load .env (for local testing)
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

@app.get("/")
def root():
    return {"status": "DVS backend is live!"}

@app.get("/earthquakes")
def get_earthquakes():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, latitude, longitude, mag, place, time
        FROM earthquakes
        ORDER BY time DESC
        LIMIT 200
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [
        {"id": r[0], "lat": r[1], "lng": r[2],
         "mag": r[3], "place": r[4], "time": r[5].isoformat()}
        for r in rows
    ]
