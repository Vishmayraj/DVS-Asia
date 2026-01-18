import json
import psycopg2
from dotenv import load_dotenv
import os
import time

while True:
    try:
        #connecting to db
        load_dotenv()

        conn = psycopg2.connect(
            dbname = os.getenv("DB_NAME"),
            user = os.getenv("DB_USER"),
            password = os.getenv("DB_PASS")
        )

        cur = conn.cursor()

        with open('data/gdacs.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        latest = {}
        for f in data["features"]:
            p = f["properties"]
            if not (p.get("iscurrent") == "true" or p.get("iscurrent") is True):
                continue 

            eid = p["eventid"]
            if eid not in latest or p["datemodified"] > latest[eid]["properties"]["datemodified"]:
                latest[eid] = f


        for f in latest.values():
            p = f["properties"]

            ev_id = p["eventid"]
            ev_type = p["eventtype"]
            desc = p["htmldescription"]
            score = p["alertscore"]
            org_country = p["country"]
            fromdate = p["fromdate"]
            todate = p["todate"]
            datemodified = p["datemodified"]
            iscurrent = p["iscurrent"]
            geom_url = p["url"]["geometry"]
            report_url = p["url"]["report"]

            if ev_type in ('EQ', 'WF'):
                continue

            aff_countries = ", ".join([c["countryname"] for c in p.get("affectedcountries", [])])
            sev = p.get("severitydata", {})
            severity = sev.get("severity")
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
            SET type = EXCLUDED.type,
                description = EXCLUDED.description,
                score = EXCLUDED.score,
                org_country = EXCLUDED.org_country,
                from_date = EXCLUDED.from_date,
                to_date = EXCLUDED.to_date,
                date_modified = EXCLUDED.date_modified,
                affectedcountries = EXCLUDED.affectedcountries,
                severity = EXCLUDED.severity,
                severitytext = EXCLUDED.severitytext,
                severityunit = EXCLUDED.severityunit,
                iscurrent = EXCLUDED.iscurrent,
                geom_url = EXCLUDED.geom_url,
                report_url = EXCLUDED.report_url
            """, (
                ev_id, ev_type, desc, score, org_country,
                fromdate, todate, datemodified, aff_countries,
                severity, severitytext, severityunit, iscurrent,
                geom_url, report_url
            ))

            print(f"Inserted {ev_type} {ev_id} (modified {datemodified})")

        conn.commit()
        cur.close()
        conn.close()

        print("✅ Cycle complete, waiting 10s...")
        time.sleep(10)
    
    except Exception as e:
        print('Error', e)
        time.sleep(30)