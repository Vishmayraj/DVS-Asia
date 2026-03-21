# DATA INGESTION PIPELINE FOR GDACS ALERTS (floods, cyclones, droughts)

import requests
import psycopg2
import json
from dotenv import load_dotenv
import os
import time
from pathlib import Path

WAIT_TIME = 30
GDACS_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/MAP"
SKIP_TYPES = {"EQ", "WF"}

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(env_path)


def fetch_geometry(geom_url):
    try:
        res = requests.get(geom_url, timeout=15)
        res.raise_for_status()
        return res.json()
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

        # keep only the latest version of each current event
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

        # fetch geometry for any row that doesn't have it yet
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

        # remove events that are no longer current
        cur.execute("DELETE FROM gdacs_live WHERE iscurrent = false")
        expired = cur.rowcount

        conn.commit()
        cur.close()

        print(f"inserted={inserted} updated={updated} geom_fetched={geom_fetched} expired_removed={expired} | waiting {WAIT_TIME}s...")

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

    time.sleep(WAIT_TIME)