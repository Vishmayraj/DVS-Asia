# DATA INGESTION PIPELINE FOR GDACS ALERTS (floods, cyclones, droughts)

import requests
import psycopg2
import json
import os
import sys
from dotenv import load_dotenv
import time
from pathlib import Path
from shapely.geometry import shape, mapping
from shapely.ops import unary_union


WAIT_TIME = 30
RUN_ONCE = "--once" in sys.argv
GDACS_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/MAP"
SKIP_TYPES = {"EQ", "WF"}

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(env_path)

SIMPLIFY_TOLERANCE = 0.01   # ~1 km; raise to 0.05 for even smaller payloads
COORD_PRECISION    = 4      # decimal places kept per coordinate


def round_coords(geom_dict):
    """Recursively round all coordinate values in a GeoJSON geometry dict."""
    def _round(obj):
        if isinstance(obj, list):
            return [_round(i) for i in obj]
        if isinstance(obj, float):
            return round(obj, COORD_PRECISION)
        return obj
    result = dict(geom_dict)
    result["coordinates"] = _round(result.get("coordinates", []))
    return result


def simplify_geometry(geom_data):
    """
    Accept a raw GDACS FeatureCollection, simplify all polygon/line geometries,
    and return a single GeoJSON geometry dict (or None on failure).
    """
    if not geom_data or geom_data.get("type") != "FeatureCollection":
        return geom_data

    shapes = []
    for feature in geom_data.get("features", []):
        geom = feature.get("geometry")
        if not geom:
            continue
        try:
            shapes.append(shape(geom))
        except Exception:
            continue

    if not shapes:
        return None

    try:
        merged    = unary_union(shapes)
        simplified = merged.simplify(SIMPLIFY_TOLERANCE, preserve_topology=True)
        result    = round_coords(mapping(simplified))
        return result
    except Exception as e:
        print(f"  simplify failed, storing raw geometry: {e}")
        # fall back to the raw first geometry so we don't lose the event
        raw = geom_data["features"][0].get("geometry")
        return round_coords(raw) if raw else None


def fetch_geometry(geom_url):
    try:
        res = requests.get(geom_url, timeout=15)
        res.raise_for_status()
        raw = res.json()
        return simplify_geometry(raw)   # <-- simplify before returning
    except Exception as e:
        print(f"  geometry fetch failed for {geom_url}: {e}")
        return None


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

        response = requests.get(GDACS_URL, timeout=15)
        response.raise_for_status()
        data = response.json()

        latest = {}
        for feature in data["features"]:
            p = feature["properties"]
            if not p.get("iscurrent"):
                continue
            eid = p["eventid"]
            if eid not in latest or p["datemodified"] > latest[eid]["properties"]["datemodified"]:
                latest[eid] = feature

        inserted = 0
        updated = 0
        geom_fetched = 0

        for feature in latest.values():
            p = feature["properties"]

            ev_type = p["eventtype"]
            if ev_type in SKIP_TYPES:
                continue

            ev_id        = p["eventid"]
            desc         = p["htmldescription"]
            score        = p["alertscore"]
            org_country  = p["country"]
            fromdate     = p["fromdate"]
            todate       = p["todate"]
            datemodified = p["datemodified"]
            iscurrent    = p["iscurrent"]
            geom_url     = p["url"]["geometry"]
            report_url   = p["url"]["report"]

            aff_countries = ", ".join(
                [c["countryname"] for c in p.get("affectedcountries", [])]
            )
            sev          = p.get("severitydata", {})
            severity     = sev.get("severity")
            severitytext = sev.get("severitytext")
            severityunit = sev.get("severityunit")

            cur.execute("""
                INSERT INTO gdacs_live (
                    id, type, description, score, org_country,
                    from_date, to_date, date_modified, affectedcountries,
                    severity, severitytext, severityunit, iscurrent,
                    geom_url, report_url
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT ON CONSTRAINT gdacs_unique DO UPDATE
                    SET type              = EXCLUDED.type,
                        description       = EXCLUDED.description,
                        score             = EXCLUDED.score,
                        org_country       = EXCLUDED.org_country,
                        from_date         = EXCLUDED.from_date,
                        to_date           = EXCLUDED.to_date,
                        date_modified     = EXCLUDED.date_modified,
                        affectedcountries = EXCLUDED.affectedcountries,
                        severity          = EXCLUDED.severity,
                        severitytext      = EXCLUDED.severitytext,
                        severityunit      = EXCLUDED.severityunit,
                        iscurrent         = EXCLUDED.iscurrent,
                        geom_url          = EXCLUDED.geom_url,
                        report_url        = EXCLUDED.report_url
                    WHERE gdacs_live.date_modified IS DISTINCT FROM EXCLUDED.date_modified
            """, (
                ev_id, ev_type, desc, score, org_country,
                fromdate, todate, datemodified, aff_countries,
                severity, severitytext, severityunit, iscurrent,
                geom_url, report_url
            ))

            if cur.rowcount == 1:
                if cur.statusmessage.startswith("UPDATE"):
                    updated += 1
                else:
                    inserted += 1

        conn.commit()

        cur.execute("SELECT id, geom_url FROM gdacs_live WHERE geometry IS NULL")
        missing_geom = cur.fetchall()

        for row_id, row_geom_url in missing_geom:
            geom_data = fetch_geometry(row_geom_url)
            if geom_data:
                cur.execute(
                    "UPDATE gdacs_live SET geometry = %s WHERE id = %s",
                    (json.dumps(geom_data), row_id)
                )
                geom_fetched += 1
                time.sleep(0.5)

        conn.commit()

        cur.execute("DELETE FROM gdacs_live WHERE iscurrent = false")
        expired = cur.rowcount

        conn.commit()
        cur.close()

        print(f"inserted={inserted} updated={updated} geom_fetched={geom_fetched} expired_removed={expired} | {'done.' if RUN_ONCE else f'waiting {WAIT_TIME}s...'}")

    except requests.exceptions.Timeout:
        print("GDACS request timed out, retrying...")

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