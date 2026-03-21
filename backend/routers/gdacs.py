# Router for GDACS alert endpoints

from fastapi import APIRouter, HTTPException
from backend.db import pool

router = APIRouter(prefix="/gdacs", tags=["gdacs"])


@router.get("")
def get_gdacs():
    conn = pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, type, description, score, org_country,
                   from_date, to_date, affectedcountries,
                   severity, severitytext, severityunit,
                   geom_url, report_url
            FROM gdacs_live
            ORDER BY from_date DESC
        """)
        rows = cur.fetchall()
        cur.close()
        return [
            {
                "id":               r[0],
                "type":             r[1],
                "description":      r[2],
                "score":            r[3],
                "org_country":      r[4],
                "from_date":        r[5].isoformat() if r[5] else None,
                "to_date":          r[6].isoformat() if r[6] else None,
                "affectedcountries": r[7],
                "severity":         r[8],
                "severitytext":     r[9],
                "severityunit":     r[10],
                "geom_url":         r[11],
                "report_url":       r[12],
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        pool.putconn(conn)