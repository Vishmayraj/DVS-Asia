# DATA INGESTION PIPELINE FOR FLOODS/CYCLONES/DROUGHTS FROM GDACS

import requests
import psycopg2
from dotenv import load_dotenv
import os
import time
from pathlib import Path

WAIT_TIME = 30
GDACS_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/MAP"
SKIP_TYPES = {"EQ", "WF"}

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

while True:
    conn = None
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
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
            if str(p.get("iscurrent")).lower() != "true":
                continue
            eid = p["eventid"]
            if eid not in latest or p["datemodified"] > latest[eid]["properties"]["datemodified"]:
                latest[eid] = feature

        inserted = 0
        updated = 0

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
            sev           = p.get("severitydata", {})
            severity      = sev.get("severity")
            severitytext  = sev.get("severitytext")
            severityunit  = sev.get("severityunit")

            cur.execute("""
                INSERT INTO gdacs_live (
                    id, type, description, score, org_country,
                    from_date, to_date, date_modified, affectedcountries,
                    severity, severitytext, severityunit, iscurrent,
                    geom_url, report_url
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT ON CONSTRAINT gdacs_unique DO UPDATE
                    SET type             = EXCLUDED.type,
                        description      = EXCLUDED.description,
                        score            = EXCLUDED.score,
                        org_country      = EXCLUDED.org_country,
                        from_date        = EXCLUDED.from_date,
                        to_date          = EXCLUDED.to_date,
                        date_modified    = EXCLUDED.date_modified,
                        affectedcountries = EXCLUDED.affectedcountries,
                        severity         = EXCLUDED.severity,
                        severitytext     = EXCLUDED.severitytext,
                        severityunit     = EXCLUDED.severityunit,
                        iscurrent        = EXCLUDED.iscurrent,
                        geom_url         = EXCLUDED.geom_url,
                        report_url       = EXCLUDED.report_url
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

        # remove events that are no longer current
        cur.execute("""
            DELETE FROM gdacs_live
            WHERE LOWER(iscurrent::text) != 'true'
        """)
        expired = cur.rowcount

        conn.commit()
        cur.close()

        print(f"inserted={inserted} updated={updated} expired_removed={expired} | waiting {WAIT_TIME}s...")

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