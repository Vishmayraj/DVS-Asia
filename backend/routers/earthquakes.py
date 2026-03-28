# Router for earthquake endpoints

from fastapi import APIRouter, HTTPException
from backend.db import pool

router = APIRouter(prefix="/earthquakes", tags=["earthquakes"])


@router.get("")
def get_earthquakes():
    conn = None
    try:
        conn = pool.getconn()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, latitude, longitude, mag, magtype, depth, tsunami, sig, place, time
            FROM earthquakes
            ORDER BY time DESC
        """)
        rows = cur.fetchall()
        cur.close()
        return [
            {
                "id":      r[0],
                "lat":     r[1],
                "lng":     r[2],
                "mag":     r[3],
                "magtype": r[4],
                "depth":   r[5],
                "tsunami": r[6],
                "sig":     r[7],
                "place":   r[8],
                "time":    r[9].isoformat(),
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            pool.putconn(conn)


@router.get("/archive")
def get_earthquakes_archive():
    conn = None
    try:
        conn = pool.getconn()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, latitude, longitude, mag, place, time
            FROM earthquakes_archive
            ORDER BY time DESC
        """)
        rows = cur.fetchall()
        cur.close()
        return [
            {
                "id":    r[0],
                "lat":   r[1],
                "lng":   r[2],
                "mag":   r[3],
                "place": r[4],
                "time":  r[5].isoformat(),
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            pool.putconn(conn)