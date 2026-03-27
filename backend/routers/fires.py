# Router for FIRMS fire endpoints

from fastapi import APIRouter, HTTPException, Query
from backend.db import pool

router = APIRouter(prefix="/firms_fires", tags=["fires"])

VALID_SOURCES = {
    "goes":  "firms_goes_nrt",
    "modis": "firms_modis_nrt",
    "noaa20": "firms_viirs_noaa20_nrt",
    "noaa21": "firms_viirs_noaa21_nrt",
    "snpp":  "firms_viirs_snpp_nrt",
}



@router.get("")
def get_fires(source: str = Query(..., description="Satellite source: goes, modis, noaa20, noaa21, snpp")):
    if source not in VALID_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source '{source}'. Valid options: {list(VALID_SOURCES.keys())}"
        )

    table = VALID_SOURCES[source]
    conn = pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT latitude, longitude, confidence, frp,
                   daynight, acq_date, acq_time, satellite, instrument
            FROM {table}
        """)
        rows = cur.fetchall()
        cur.close()
        return [
            {
                "lat":        r[0],
                "lng":        r[1],
                "confidence": r[2],
                "frp":        r[3],
                "daynight":   r[4],
                "acq_date":   str(r[5]) if r[5] else None,
                "acq_time":   r[6],
                "satellite":  r[7],
                "instrument": r[8],
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        pool.putconn(conn)


@router.get("/summary")
def get_fires_summary():
    """
    Returns a unified count of unique fire incidents across all sources.
    Clusters detections within a 0.1 degree grid (~11km) and deduplicates 
    across the 5 satellite sources.
    """
    conn = pool.getconn()
    try:
        cur = conn.cursor()
        # Union all sources and group by rounded coordinates for grid clustering
        cur.execute("""
            WITH all_detections AS (
                SELECT latitude, longitude FROM firms_goes_nrt
                UNION ALL
                SELECT latitude, longitude FROM firms_modis_nrt
                UNION ALL
                SELECT latitude, longitude FROM firms_viirs_noaa20_nrt
                UNION ALL
                SELECT latitude, longitude FROM firms_viirs_noaa21_nrt
                UNION ALL
                SELECT latitude, longitude FROM firms_viirs_snpp_nrt
            )
            SELECT COUNT(DISTINCT (ROUND(latitude::numeric, 1), ROUND(longitude::numeric, 1)))
            FROM all_detections
        """)
        count = cur.fetchone()[0]
        cur.close()
        return {"count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        pool.putconn(conn)