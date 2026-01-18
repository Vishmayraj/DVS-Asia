# 🔥 **DVS — Disaster Visualization System**

_A journey from chaos to clean, structured, real-time data._

---

## 🌍 What This Project Is

DVS is a living system that pulls **satellite fire data** and **earthquake events** in real time, cleans them, stores them in PostgreSQL, and keeps everything automatically deduplicated.

What started as a “let’s just store some fire data” experiment slowly evolved into a full **data ingestion pipeline** —  
one that could eventually power a live, interactive disaster dashboard.

Every step — the tables, the constraints, the debugging — was about making data _flow_ smoothly and truthfully.

---
## 🔥 Fire Ingestion Pipeline (NASA FIRMS)

This module handles **real-time ingestion of fire detection data** from NASA’s **FIRMS (Fire Information for Resource Management System)** API.  
It’s one of the core ingestion pipelines in DVS — alongside earthquakes, floods, cyclones, and droughts — and is designed to run continuously, storing only the **most current fire data** across multiple satellites.

---

### 🛰️ Overview

FIRMS provides thermal anomaly (fire) detections from several satellite instruments in near-real time.  
Each satellite produces slightly different readings and update frequencies, so this pipeline treats them independently.

We currently ingest five data sources:

|Source|Satellite|Description|
|---|---|---|
|**VIIRS_NOAA20_NRT**|NOAA-20|Near-Real-Time VIIRS sensor|
|**VIIRS_NOAA21_NRT**|NOAA-21|Newer VIIRS platform|
|**VIIRS_SNPP_NRT**|Suomi NPP|VIIRS on Suomi National Polar-orbiting Partnership|
|**MODIS_NRT**|Terra/Aqua|MODIS thermal sensors|
|**GOES_NRT**|Himawari / Meteosat|Geostationary rapid updates|

Each one gets its own table in PostgreSQL:

`firms_viirs_noaa20_nrt firms_viirs_noaa21_nrt firms_viirs_snpp_nrt firms_modis_nrt firms_goes_nrt`

This design keeps debugging, updates, and performance clean — each satellite behaves independently, so there’s no data collision.

---

### 🧩 Data Structure

Every FIRMS dataset shares the same column structure, which directly maps into SQL tables:

|Column|Description|
|---|---|
|`latitude`, `longitude`|Fire detection coordinates|
|`bright_ti4`, `bright_ti5`|Brightness of thermal bands|
|`scan`, `track`|Pixel size and scan geometry|
|`acq_date`, `acq_time`|Acquisition timestamp|
|`satellite`, `instrument`|Source metadata|
|`confidence`|Detection certainty (`l`, `n`, `h`, or `%`)|
|`version`|FIRMS dataset version (e.g., `2.0NRT`)|
|`frp`|Fire Radiative Power (intensity)|
|`daynight`|Day (`D`) or night (`N`) observation|

---

### ⚙️ Deduplication via Constraints

NASA FIRMS data often re-sends the same detections as the feed refreshes.  
To avoid redundant inserts, every table includes a **unique constraint**:

`UNIQUE (   latitude,   longitude,   acq_date,   acq_time,   satellite,   instrument,   confidence,   frp )`

During ingestion, if a new row violates this constraint, PostgreSQL quietly skips it.  
This keeps the data **deduplicated automatically**, no manual filtering required.

---

### 🔄 Real-Time Refresh Logic

Since FIRMS only provides **current detections for the last day**, there’s no need to archive historical data here.  
Instead, this pipeline keeps tables “live” — replacing their entire content whenever the dataset changes.

To do this efficiently, the script computes a **hash** (checksum) of each downloaded CSV.

If the hash changes → the table is truncated and refreshed.  
If it’s the same → the update is skipped.

This prevents needless re-inserts and makes the pipeline lightweight even when running every few seconds.

---

### 🧠 Persistent Hash Tracking

To make the system **restart-safe**, each satellite’s last known hash is stored in a local file:

`/state/hashes.json`

Example:

`{   "VIIRS_NOAA20_NRT": "a4f8b32d3adf0d3b9a8cbe3b5f293c21",   "VIIRS_NOAA21_NRT": "d1bfa8c473a1ad7aeb83e71f5d13f9a4" }`

On every cycle:

- The new CSV is fetched.
    
- Its hash is computed.
    
- If the hash differs from what’s stored → the table refreshes and the file updates.
    
- Otherwise, it logs “No change detected.”
    

This design ensures the system **remembers state across restarts** — it won’t refetch old data after rebooting.

---

### 🧰 Environment Configuration

All sensitive keys and credentials live in `.env`:

`MAP_KEY=your_firms_api_key DB_USER=postgres DB_PASS=yourpassword DB_NAME=dvs`

The script loads these automatically via `python-dotenv`.

---

### 🗺️ Geographic Focus

Each API request fetches only **Asia** using a bounding box filter:

`asia_coords = "60,5,150,55"`

This keeps transactions well within FIRMS limits (5000/10min),  
and ensures DVS focuses on one disaster-rich, diverse region.

---

### 📊 Behavior Summary

|Behavior|Description|
|---|---|
|**Update Frequency**|~Every 30 seconds (configurable)|
|**Duplication Handling**|PostgreSQL unique constraints|
|**Refresh Strategy**|Hash-based change detection + table truncation|
|**Scope**|Asia bounding box|
|**Data Lifetime**|Current-day fires only|
|**Persistence**|Hashes stored in `hashes.json`|

---

### 🧡 The Journey

This pipeline started as “let’s just store some FIRMS data”  
and evolved into a **self-aware ingestion engine** that:

- Talks to five satellites independently
    
- Detects changes before rewriting
    
- Cleans and deduplicates automatically
    
- Persists its state safely between runs
    

Now it runs silently — fetching, checking, cleaning, and refreshing —  
a heartbeat of the DVS ecosystem. 🌍🔥

---

## 🌋 Earthquake Ingestion Pipeline (USGS)

This module handles real-time ingestion of global earthquake data from the **USGS (United States Geological Survey)** Earthquake API.  
It’s one of the core ingestion systems in the DVS — standing proudly beside fires, floods, cyclones, and droughts — and is designed to hum quietly in the background, catching the planet’s every shake.

---

### 🧭 Overview

The USGS Earthquake API provides near real-time updates on seismic activity across the globe.  
Each event includes detailed metadata — from magnitude and depth to location precision and seismic significance — all accessible via a simple GeoJSON endpoint.

Our pipeline continuously fetches this data for **Asia**, filtering by a bounding box.  
While earthquakes are momentary, their records are permanent — so this module smartly manages what to keep live, and what to archive.

---

### 🌍 Geographic Focus

Each API request is bounded to cover **Asia**, using the following coordinates:

`minlatitude = -10 maxlatitude = 80 minlongitude = 25 maxlongitude = 170`

This roughly captures the Asian continent (yes, Alaska sneaks in a little — we’ll forgive it).

---

### 🧩 Data Structure

Each earthquake event carries dozens of fields, but only a few truly matter for disaster visualization and analysis.  
Our ingestion pipeline extracts and stores only the essentials:

|Column|Description|
|---|---|
|id|Unique USGS event identifier|
|latitude, longitude|Epicenter coordinates|
|depth|Depth of the quake (in km)|
|mag|Magnitude of the quake|
|magtype|Magnitude scale (mb, mww, etc.)|
|time|Event occurrence timestamp (UTC)|
|tsunami|1 if tsunami potential, else 0|
|sig|Significance score (higher = more notable)|
|place|Human-readable location string|

Everything else — like “felt”, “cdi”, or “gap” — is gracefully ignored. We’re here for clean, actionable data, not a thesis.

---

### ⚙️ Table Design

Two PostgreSQL tables power this system:

|Table|Purpose|
|---|---|
|**earthquakes**|Live, rolling table — contains the last 30 days of seismic activity|
|**earthquakes_archive**|Long-term storage — a full historical record of all quakes|

This design keeps live data fast and light, while the archive holds the earth’s entire emotional history.

---

### 🧠 Deduplication

Each event’s `id` serves as a **primary key**, ensuring no duplicates ever sneak in.

During ingestion, the query uses:

`ON CONFLICT (id) DO NOTHING`

If the USGS re-sends an event with the same ID, PostgreSQL politely nods and skips it — no fuss, no redundancy.

---

### 🔄 Real-Time Ingestion Logic

The script continuously:

1. Fetches the latest GeoJSON feed from the USGS API.
    
2. Parses each event and inserts it into both **earthquakes** and **earthquakes_archive**.
    
3. Deletes events older than **30 days** from the live table.
    

This ensures the live table remains sleek and current, while the archive grows infinitely wiser.

**Update Frequency:** ~Every 30 seconds (configurable).

---

### 🧹 Data Retention Strategy

- **Live table:** Keeps only the most recent 30 days of data.
    
- **Archive table:** Stores everything, forever.
    
- **Yearly reset:** When a new year begins, the system seamlessly continues inserting new data while older entries remain safe in the archive.
    

If you check back in March to find a January quake — it’ll still be there, just living quietly in `earthquakes_archive`.

---

### 🧰 Environment Configuration

As always, secrets and configuration live in `.env`:

`DB_NAME=earthquakes DB_USER=postgres DB_PASS=yourpassword`

The script automatically loads these with `python-dotenv`.

---

### ⚡ Behavior Summary

| Behavior             | Description                                |
| -------------------- | ------------------------------------------ |
| Update Frequency     | ~Every 30 seconds (configurable)           |
| Duplication Handling | PostgreSQL primary key on `id`             |
| Refresh Strategy     | Continuous insert + 30-day rolling cleanup |
| Scope                | Asia bounding box                          |
| Data Lifetime        | 30 days live, infinite in archive          |
| Persistence          | Managed in PostgreSQL                      |

---

### 💡 The Journey

This pipeline started as “let’s just store some earthquake data”  
and quickly evolved into a lean, self-managing ingestion engine that:

- Watches Asia tremble in real time
    
- Cleans itself every 30 days
    
- Archives everything neatly for eternity
    
- Never loses a quake, even during a reboot
    

Now it runs quietly — fetching, inserting, archiving, and cleaning —  
a steady heartbeat in the DVS ecosystem. 🌏💥


---

## 🧩 Database State

Everything lives inside a single PostgreSQL database, renamed simply to **`dvs`**.

Current size: **~16 MB.**  
That’s tiny, considering it stores daily disaster detections for an entire continent —  
proof that good structure scales gracefully.

---

## 🔐 The Hidden File

Configuration stays private inside a `.env` file:

`MAP_KEY=my_firms_api_key DB_USER=postgres DB_PASS=passmyword DB_NAME=dvs`

That keeps secrets out of GitHub and your terminal history —  
a small practice, but crucial when you automate live ingestion.

---

## 🧠 What I Learned

- FIRMS is not one dataset — it’s an ecosystem.
    
- Separate tables are sanity savers.
    
- `ON CONFLICT DO NOTHING` is the chillest line of SQL you’ll ever write.
    
- Brightness and FRP together tell deeper stories than coordinates alone.
    
- Numerical data barely eats space; duplication does.
    
- Confidence isn’t computed — it’s NASA’s own probability model.
    
- If you think you’re “inserting 3000 new rows”… check your `print()` first 😂.
    

---

## 🚀 Next Up

- Combine all feeds visually on a live map (Leaflet/Mapbox).
    
- Add auto-purge logic for older data (30–60 days).
    
- Track true insert counts per run.
    
- Expose an internal REST API for visualization layers.
    

---

## 🔥 **GDACS Ingestion Pipeline (Global Disaster Alerts)**

This module handles real-time ingestion of global disaster event data from **GDACS** (Global Disaster Alert and Coordination System).  
It’s one of the core ingestion pipelines in **DVS** — alongside FIRMS fires, USGS earthquakes, cyclones, droughts, and more — and is designed to run continuously, storing only the most **current, live disaster events**.

---
### 🛰️ **Overview**

GDACS provides near-real-time alerts for floods, tropical cyclones, droughts, and other disasters.  
Each event is constantly updated, and new polygons or severity readings may appear over time.  
Unlike some other feeds, GDACS gives you multiple “episodes” of the same event — so we only keep the **latest episode per event** for performance and sanity.

---
### 📡 **Event Types**

| Type   | Meaning          | Notes                         |
| ------ | ---------------- | ----------------------------- |
| FL     | Flood            | Water on the move 🌊          |
| TC     | Tropical Cyclone | Windy business 🌪️            |
| DR     | Drought          | Thirsty lands 🌵              |
| EQ     | Earthquake       | Handled by USGS pipeline ⚡    |
| WF     | Wildfire         | Handled by FIRMS pipeline 🔥  |
| Others | …                | Rare events we ignore for now |

---
### 🧩 **Data Structure**

Every GDACS event is ingested as a JSON **Feature**, containing:

| Field                                  | Description                           |
| -------------------------------------- | ------------------------------------- |
| id                                     | Event ID (unique per event)           |
| type                                   | Event type (FL, TC, DR…)              |
| description                            | Human-readable summary                |
| score                                  | GDACS alert score (intensity proxy)   |
| org_country                            | Country reporting the event           |
| from_date / to_date                    | Event duration                        |
| date_modified                          | Last GDACS update timestamp           |
| affectedcountries                      | Comma-separated affected countries    |
| severity / severitytext / severityunit | Event intensity                       |
| iscurrent                              | Boolean — event is active?            |
| geom_url                               | Link to polygon/geometry for plotting |
| report_url                             | GDACS event report page               |

### ⚙️ **Deduplication & Latest Updates**

GDACS events can have **multiple features per ID**, sometimes differing only slightly in geometry.  
We only store the **latest `datemodified` per `eventid`** and skip everything else.  
This keeps the DB lean while still giving you accurate map plotting.

SQL constraints ensure uniqueness:

`UNIQUE (id, type)`

…so if the same event pops up again, PostgreSQL quietly updates its fields instead of creating duplicates.

---
### 🔄 **Real-Time Refresh Logic**

Since GDACS constantly pushes updates:

1. Fetch the latest JSON from the GDACS API.
    
2. Filter out inactive events (`iscurrent != true`).
    
3. Keep only the latest feature per event (`datemodified`).
    
4. Skip earthquakes and fires — they’re handled by separate pipelines.
    
5. Insert/update live events into `gdacs_live` table.
    

The loop runs **continuously**, with a 10–30 second delay between cycles to respect API limits.

---
### 🧠 **Lazy Geometry Fetching**

Full polygons can be huge (hundreds to thousands of coordinates).  
We **don’t store them directly** — only the URL.  
Polygons are fetched **on-demand**, e.g., when plotting maps, which keeps ingestion fast and the database light.

---
### 🧰 **Environment Configuration**

All sensitive credentials live in `.env`:

`DB_NAME=dvs DB_USER=postgres DB_PASS=yourpassword`

Loaded via `python-dotenv` automatically.

---
### 📊 **Behavior Summary**

|Behavior|Description|
|---|---|
|Update Frequency|~Every 10–30s (configurable)|
|Deduplication|PostgreSQL unique constraints + latest `datemodified`|
|Refresh Strategy|Continuous fetch + filtering of inactive events|
|Scope|Global alerts|
|Data Lifetime|Only **current, active disasters**|
|Geometry Handling|Lazy fetch via `geom_url`|
|Exclusions|Earthquakes & wildfires (handled by separate pipelines)|

---
### 🧡 **The Journey**

This pipeline began as “let’s just dump GDACS JSON somewhere” and evolved into a **self-cleaning, live disaster ingestion engine**:

- Fetches updates continuously
    
- Keeps only relevant, current events
    
- Avoids duplication
    
- Stores lightweight live summaries for plotting
    
- Defers heavy polygon fetching to when you actually need it
    

Now it runs quietly in the background, **keeping your live disaster map accurate and snappy** 🌍💥

---

## 🌐 Why Hasn’t Anyone Already Done This?

That question stuck with me from the start.  
If NASA, USGS, and ReliefWeb already publish everything,  
why doesn’t the world have a single map that just… _shows it all_?

Turns out, the reasons are both **technical** and **human**.

---

### ⚙️ 1. The Data Is a Mess

Every disaster type speaks its own language.

|Disaster|Main Source|Format|Typical Update|
|---|---|---|---|
|Earthquakes|USGS|GeoJSON|Every few seconds|
|Wildfires|NASA FIRMS|CSV / GeoTIFF|Every few hours|
|Floods|ReliefWeb|JSON|Irregular|
|Cyclones|NOAA / IMD|XML / shapefile|Every few hours|
|Volcanoes|Smithsonian / USGS|JSON|Irregular|

Different timestamps. Different coordinate systems. Missing fields. Contradictions.  
Most projects die right here — data cleaning eats 80% of the timeline _before_ visualization even starts.

---

### ⏱️ 2. “Real-Time” Isn’t Really Real-Time

NASA’s fire data lags by hours.  
Earthquakes can be revised.  
Cyclones change course mid-feed.

Show too early — you spread false alarms.  
Show too late — you lose relevance.  
So most dashboards pick one domain: fire, quake, or weather. Never all.

---

### 🔒 3. APIs Have Limits

Every source imposes:

- Rate limits
    
- Tokens or registration
    
- Quotas per minute/hour
    
- Gigantic payloads
    

You can’t just “refresh everything.” You need queues, caching, deduplication —  
real infrastructure, not spreadsheets.

---

### 🧩 4. The Cross-Discipline Gap

To build this right, you need to be part:

- Data engineer
    
- Geospatial scientist
    
- Cloud developer
    
- Designer
    

That’s four hats few teams wear at once.

---

### 🏛️ 5. Institutions Build for Themselves, Not the Public

UN, NASA, NOAA — they already monitor everything.  
But their tools are made for **research**, not real-time public insight.

Google’s _Crisis Map_ (2012-2021) tried to unify it all — and worked —  
until maintaining live data validation became too costly.

So a vacuum remains:  
all the data exists, but no unified, open, human-readable map connects it.

---

## 💡 Why Do It Anyway?

Because now, the hard parts are solvable.

We have APIs, free databases, cloud schedulers, and open data —  
the only missing piece is someone who ties them together _cleanly_.

That’s where **DVS** comes in.

---

## 🌏 My Approach

Instead of chasing the whole planet, I focused on **Asia** —  
big, diverse, disaster-prone, and rich with data sources.

By fetching all events within bounding boxes,  
I get precise regional data at low transaction cost.

Each disaster type lives in its own table,  
each table follows a common schema,  
and a single refresh loop keeps everything in sync.

No duplication. No blind inserts. No waiting for grants.  
Just clean, automated data from five satellites and one planet.

---

**Built by Zala Vishmayraj⚡**  
Because the planet never sleeps — and neither should our data.

---
