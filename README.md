# 🔥 **DVS — Disaster Visualization System**

_A journey from chaos to clean, structured, real-time data._

---

## 🌍 What This Project Is

DVS is a living system that pulls **satellite fire data** and **earthquake events** in real time, cleans them, stores them in PostgreSQL, and keeps everything automatically deduplicated.

What started as a “let’s just store some fire data” experiment slowly evolved into a full **data ingestion pipeline** —  
one that could eventually power a live, interactive disaster dashboard.

Every step — the tables, the constraints, the debugging — was about making data _flow_ smoothly and truthfully.

---

## 🛰️ The Fire Data Saga

It began with NASA’s **FIRMS** (Fire Information for Resource Management System) API.  
Turns out, FIRMS doesn’t give you _a_ fire list — it gives you _many_, each from a different satellite or mode.

I used five of them:

|Source|Description|
|---|---|
|**VIIRS_NOAA20_NRT**|VIIRS sensor on the NOAA-20 satellite (Near Real Time)|
|**VIIRS_NOAA21_NRT**|Same VIIRS sensor, newer satellite|
|**VIIRS_SNPP_NRT**|The Suomi NPP satellite’s VIIRS feed|
|**MODIS_NRT**|The classic Terra/Aqua MODIS sensors|
|**GOES_NRT**|Geostationary satellites (big, fast coverage)|

At first, I thought merging them all into one table would simplify things.  
It didn’t — each behaves differently.

So now, **each satellite has its own table**.  
That decision made everything cleaner: easier debugging, isolated failures, and independent schedules.

---

## 💾 The Tables

Each satellite table follows the same schema — directly inspired by FIRMS’ CSV format.

|Column|Description|
|---|---|
|`latitude`, `longitude`|Where the fire was detected|
|`bright_ti4`, `bright_ti5`|Thermal band brightness|
|`scan`, `track`|Pixel dimensions (precision)|
|`acq_date`, `acq_time`|When it was captured|
|`satellite`, `instrument`|Source identifiers|
|`confidence`|Detection confidence (L/N/H or %)|
|`version`|Dataset version|
|`frp`|Fire Radiative Power — intensity|
|`daynight`|Captured during day or night|

The tricky part?  
FIRMS _re-sends_ the same fire points across updates. Without protection, you’ll get thousands of duplicates.

That’s when **PostgreSQL constraints** became my best friend (and worst enemy).

---

## ⚙️ The Great Constraint Battle

At first, I assumed this was enough:

`(latitude, longitude, acq_date, acq_time)`

It wasn’t.  
FIRMS happily reuses those but tweaks confidence or FRP.

After many “duplicate key” errors and constraint rebuilds, I landed on the perfect uniqueness set:

`(latitude, longitude, acq_date, acq_time, satellite, instrument, confidence, frp)`

Now, every run quietly ignores repeats.

At one point, I thought the script was inserting 3,000 new rows each loop —  
turns out I was just printing the CSV length 🤦‍♂️.  
The database was calmly rejecting duplicates the whole time.

> Lesson learned: your script might lie, but your database won’t.

---

## 🌋 The Earthquake Side

Next came earthquakes — from the **USGS Earthquake Catalog API**.  
Structured, predictable, and refreshingly consistent.

It outputs GeoJSON instead of CSV, which makes parsing simpler.  
Each event comes with its own globally unique ID — no deduping headaches.

|Column|Description|
|---|---|
|`id`|Serial primary key|
|`time`|Timestamp of the quake|
|`latitude`, `longitude`, `depth`|Where and how deep|
|`mag`, `magType`|Magnitude and scale|
|`place`|Textual location|
|`status`, `tsunami`, `type`|Event metadata|

No unique constraint needed — USGS handles that beautifully.

---

## 🧩 Database State

Everything lives inside a single PostgreSQL database, renamed simply to **`dvs`**.

`public ├── earthquakes ├── firms_viirs_noaa20_nrt ├── firms_viirs_noaa21_nrt ├── firms_viirs_snpp_nrt ├── firms_modis_nrt └── firms_goes_nrt`

Current size: **~16 MB.**  
That’s tiny, considering it stores daily fire detections for an entire continent —  
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

## 🧡 The Journey

What began as _“let’s store some fire data”_ turned into a self-sustaining ingestion system —  
one that fetches, cleans, deduplicates, and stores real NASA and USGS data every few seconds.

It’s not just about building a database anymore.  
It’s about **watching the Earth breathe — through heat and tremors — in real time.**

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
