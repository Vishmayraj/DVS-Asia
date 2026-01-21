# 🔥 **DVS — Disaster Visualization System**

_A living pipeline turning chaos into structured, real-time data._

---

## 🌍 What It Is

**DVS** ingests and cleans **satellite fire** and **earthquake** data (and soon floods, cyclones, droughts), storing it in **PostgreSQL** with full deduplication and change detection.  
It began as a test script and evolved into a modular **data ingestion engine** — ready to power live, map-based disaster dashboards.

---

## 🔥 FIRMS Fire Pipeline (NASA)

Pulls **near-real-time fire detections** from NASA’s FIRMS API.  
Handles 5 independent satellite feeds:

|Source|Satellite|Purpose|
|---|---|---|
|VIIRS_NOAA20_NRT|NOAA-20|Near-Real-Time VIIRS|
|VIIRS_NOAA21_NRT|NOAA-21|Newer VIIRS|
|VIIRS_SNPP_NRT|Suomi NPP|Legacy VIIRS|
|MODIS_NRT|Terra/Aqua|MODIS sensor data|
|GOES_NRT|Geostationary|Rapid updates|

Each has its own SQL table (`firms_viirs_noaa20_nrt`, etc.) to isolate updates and debugging.

**Schema Highlights:**  
`latitude`, `longitude`, `acq_date`, `acq_time`, `satellite`, `instrument`, `confidence`, `frp`, `daynight`, etc.

**Deduplication:**  
`UNIQUE (latitude, longitude, acq_date, acq_time, satellite, instrument, confidence, frp)`

**Refresh Logic:**

- Each feed’s CSV is hashed.
    
- If hash changes → table truncated + re-filled.
    
- Otherwise skipped.
    
- Hashes stored persistently in `/state/hashes.json`.
    

**Scope:** Asia (`60,5,150,55`)  
**Update:** ~30 s loop  
**Lifetime:** Current-day detections only  
**Env:** `.env` → `MAP_KEY`, `DB_USER`, `DB_PASS`, `DB_NAME`

_Result: 5 autonomous, self-deduplicating fire pipelines._

---

## 🌋 USGS Earthquake Pipeline

Ingests **global seismic events** (GeoJSON) from USGS, filtered for **Asia**:

`minlat=-10, maxlat=80, minlon=25, maxlon=170`

**Tables:**

|Table|Purpose|
|---|---|
|`earthquakes`|Rolling 30-day live table|
|`earthquakes_archive`|Permanent historical store|

**Core Fields:**  
`id`, `latitude`, `longitude`, `depth`, `mag`, `magtype`, `time`, `tsunami`, `sig`, `place`

**Deduplication:**  
`PRIMARY KEY (id)` → `ON CONFLICT DO NOTHING`

**Loop:**  
Fetch → insert into both tables → remove >30-day data from live.  
**Update:** ~30 s  
**Lifetime:** 30 days live / permanent archive  
**Env:** same `.env` as above.

_Result: clean, rolling seismic data that never duplicates or expires silently._

---

## 🌐 GDACS Global Alerts Pipeline

Pulls real-time alerts (floods, cyclones, droughts, etc.) from **GDACS**.

**Event Types:** `FL`, `TC`, `DR` (+ others ignored)  
**Key Fields:**  
`id`, `type`, `description`, `score`, `org_country`, `from_date`, `to_date`, `date_modified`, `affectedcountries`, `severity`, `iscurrent`, `geom_url`, `report_url`

**Rules:**

- Keep only active (`iscurrent=true`) events
    
- Only latest `date_modified` per `id`
    
- Skip EQ/WF (handled elsewhere)
    
- Store geometry URLs, not polygons
    
- `UNIQUE (id, type)` ensures one active record per event
    

**Update:** every 10–30 s  
**Scope:** Global  
**Lifetime:** Only current disasters

_Result: lightweight, continuously refreshed global feed._

---

## 🧩 Database Overview

All pipelines share one database: **`dvs`**  
~16 MB for daily Asia-wide data — proof of efficient schema design.

**Secrets:** stored in `.env`  
Example:  
`MAP_KEY=... DB_USER=postgres DB_HOST=... DB_PASS=... DB_NAME=dvs`

---

## 💡 Lessons

- FIRMS = 5 unique feeds, not one.
    
- Separate tables simplify scaling.
    
- `ON CONFLICT DO NOTHING` = pure serenity.
    
- Deduplication > disk space.
    
- Confidence = NASA’s probability model, not ours.
    
- Always check hashes before assuming “new data.”
    

---

## 🚀 Next Steps

- Unified **Leaflet/Mapbox** live map
    
- Auto-purge logic for older data
    
- REST API for visualization layers
    
- Multi-source disaster overlay
    

---

## 🧠 Why DVS Exists

Despite NASA, USGS, and GDACS publishing everything,  
no unified open system **ties it all together**.  
Data formats clash, APIs throttle, and “real-time” often isn’t.

**DVS bridges that gap** — small, modular, regional, open-source,  
designed for people who want clean disaster data that _just works_.

---

**Built by Zala Vishmayraj ⚡**  
_The planet never sleeps — neither should its data._

---