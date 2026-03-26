# DisasterViz -> Asia

> Real-time disaster visualization for Asia. Satellite fire detections, seismic events, and global alerts -> unified, deduplicated, and mapped live.

**Live:** [disasterviz.onrender.com](https://disasterviz.onrender.com/)

---

## What it does

Most disaster data is public. NASA publishes satellite fire detections every few minutes. USGS streams every earthquake globally. GDACS aggregates floods, cyclones, and droughts in real time. But each source has a different format, a different API, and no unified way to visualize them together.

DisasterViz pulls from all three, stores the data cleanly in PostgreSQL, and serves it through a FastAPI backend to a Leaflet map with color-coded markers, polygon carpets for affected areas, hover tooltips, and click-through detail popups.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Data Sources                      │
│   NASA FIRMS      USGS FDSNWS      GDACS API        │
└────────┬──────────────┬────────────────┬────────────┘
         │              │                │
         ▼              ▼                ▼
┌─────────────────────────────────────────────────────┐
│         GitHub Actions (cron every 30 min)          │
│   ins_fires.py    ins_eq.py    ins_gdacs.py         │
│   (--once flag, runs and exits per cycle)           │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│              PostgreSQL (Supabase)                  │
│                                                     │
│  firms_viirs_noaa20_nrt    earthquakes              │
│  firms_viirs_noaa21_nrt    earthquakes_archive      │
│  firms_viirs_snpp_nrt      gdacs_live               │
│  firms_modis_nrt                                    │
│  firms_goes_nrt                                     │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│              FastAPI (Render)                       │
│                                                     │
│  GET /earthquakes          GET /firms_fires?source= │
│  GET /earthquakes/archive  GET /gdacs               │
│  GET /health                                        │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│           Frontend (Leaflet + Vanilla JS)           │
│   Dark/light theme · Sidebar · Mobile bottom sheet  │
└─────────────────────────────────────────────────────┘
```

Ingestion runs as GitHub Actions cron jobs every 30 minutes. Each script accepts a `--once` flag to run a single cycle and exit, keeping Actions minutes usage low. A FastAPI layer reads from the DB and serves JSON. A pure HTML/CSS/JS frontend fetches from the API and renders everything on a Leaflet map. No frameworks, no build step.

---

## Data pipelines

### Fire detections -> NASA FIRMS

NASA's Fire Information for Resource Management System publishes near-real-time fire detections from five independent satellite feeds:

| Source | Satellite | Sensor |
|--------|-----------|--------|
| VIIRS_NOAA20_NRT | NOAA-20 | VIIRS |
| VIIRS_NOAA21_NRT | NOAA-21 | VIIRS |
| VIIRS_SNPP_NRT | Suomi NPP | VIIRS |
| MODIS_NRT | Terra / Aqua | MODIS |
| GOES_NRT | Geostationary | ABI |

Each feed is stored in its own table to isolate updates. The ingestion loop hashes each feed's CSV response. If the hash matches the previous cycle, the table is left untouched. If it changes, the table is truncated and refilled using a single `execute_values` batch insert (not row-by-row). This avoids unnecessary writes while keeping data current-day fresh.

VIIRS reports confidence as a category (`h`, `n`, `l`). MODIS and GOES report it as a percentage integer. Both are handled correctly on the frontend.

Coverage: `25°W, 10°S` to `180°E, 55°N`, full Asia including Southeast Asia, Japan, and Indonesia.

### Earthquakes -> USGS

The USGS Earthquake Hazards program publishes a GeoJSON feed of seismic events queryable by bounding box. The pipeline fetches every 30 minutes, filtered to Asia (`-10° to 80°N`, `25° to 170°E`).

**Two-table design:**

- `earthquakes`: rolling 30-day live table. At the end of each cycle, events older than 30 days are moved to the archive and deleted from the live table.
- `earthquakes_archive`: permanent historical store. Events land here exactly once (`ON CONFLICT DO NOTHING`), protected by a primary key.

USGS occasionally revises magnitude and location data after initial detection. The upsert uses `ON CONFLICT DO UPDATE` with a `WHERE IS DISTINCT FROM` guard. DVS only writes to the DB if `mag`, `place`, `sig`, or `magtype` actually changed.

### GDACS alerts -> floods, cyclones, droughts

GDACS (Global Disaster Alert and Coordination System) publishes a GeoJSON event feed of active disasters. The pipeline filters out earthquakes and wildfires (handled by the other pipelines) and keeps only `iscurrent = true` events.

**Geometry storage:** Rather than fetching polygon geometry from the browser on every map load, `ins_gdacs.py` fetches each event's geometry URL once and stores the raw GeoJSON as `jsonb` in the DB. On subsequent cycles, rows with geometry already populated are skipped. This means the browser never hits the GDACS polygon API directly, it gets pre-fetched geometry from the backend.

GDACS geometry responses contain multiple features per event (`Point_Centroid`, `Poly_Affected`, `Poly_Global`). The frontend filters to `Poly_Affected` only when rendering. If no polygon exists, it falls back to the centroid point as a circle marker.

---

## API

The FastAPI backend uses `APIRouter` to separate concerns. All routes share a `psycopg2.pool.SimpleConnectionPool` (10 connections max), no new connection per request.

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /earthquakes` | Rolling 30-day seismic events |
| `GET /earthquakes/archive` | Full historical archive |
| `GET /firms_fires?source=goes\|modis\|noaa20\|noaa21\|snpp` | Fire detections by satellite |
| `GET /gdacs` | Active disaster alerts with stored geometry |

---

## Frontend

Pure HTML, CSS, and JavaScript. No React, no bundler, no build step. Leaflet 1.9.4 for the map.

**Design decisions:**

- Sidebar layout on desktop (map 70%, panel 30%). On mobile, the sidebar becomes a bottom sheet that slides up from a pill handle, the map stays full screen underneath.
- Dark and light themes, toggled via a button in both the home nav and the explorer nav. Switching theme also swaps the Leaflet tile layer between Carto Dark and Carto Light. Theme preference is persisted in `localStorage` and restored before first paint to avoid a flash.
- Earthquake markers encode magnitude in both size and color (teal < M4, yellow M4-5, orange M5-6, red M6-7, bright red M7+).
- Fire rectangles encode confidence as color (yellow = low, orange = nominal/medium, red = high). VIIRS and MODIS/GOES use different confidence formats unified at render time. Canvas renderer used for 10k+ fire shapes to avoid DOM bottlenecks.
- GDACS events render as colored polygon carpets (flood = blue, cyclone = purple, drought = yellow) where geometry is available, falling back to a circle marker at the centroid.
- Hover shows a summary tooltip. Click opens a detailed popup with all fields.
- Map is bounded to prevent world-wrapping (`maxBounds`, `worldCopyJump: false`).
- Home nav uses a floating Explorer dropdown (Syne + DM Mono, teal accents) built with Floating UI for positioning. The dropdown and source chip tooltips both use `getBoundingClientRect()` directly for placement, bypassing Floating UI's `computePosition` to avoid conflicts with the nav's `backdrop-filter` stacking context.
- The home nav hides on scroll down past 40% of the viewport height and reappears on scroll up, keeping the map preview unobstructed on landing. The explorer nav is always visible since the map is the primary interface.
- Source chips on the hero (USGS, NASA FIRMS, GDACS) show floating tooltips on hover/focus, positioned above each chip using `getBoundingClientRect()` and CSS `transform`.

---

## Local setup

### Prerequisites

- Python 3.11+
- PostgreSQL (local or Supabase)
- NASA FIRMS API key, [register here](https://firms.modaps.eosdis.nasa.gov/api/area/)

### 1. Clone and install

```bash
git clone https://github.com/Vishmayraj/DVS-Asia.git
cd DVS-Asia
pip install -r requirements.txt
```

### 2. Environment variables

Create a `.env` file in the repo root:

```env
DB_HOST=localhost
DB_NAME=dvs
DB_USER=postgres
DB_PASS=your_password
MAP_KEY=your_nasa_firms_api_key
```

### 3. Database schema

Connect to your PostgreSQL instance and run:

```sql
CREATE TABLE earthquakes (
    id        text PRIMARY KEY,
    latitude  double precision NOT NULL,
    time      timestamp NOT NULL,
    longitude double precision NOT NULL,
    depth     double precision,
    mag       real,
    magtype   varchar(10),
    tsunami   smallint,
    sig       integer,
    place     text
);

CREATE TABLE earthquakes_archive (
    id        text PRIMARY KEY,
    latitude  double precision NOT NULL,
    time      timestamp NOT NULL,
    longitude double precision NOT NULL,
    depth     double precision,
    mag       real,
    magtype   varchar(10),
    tsunami   smallint,
    sig       integer,
    place     text
);

CREATE TABLE firms_viirs_noaa20_nrt (
    id         serial,
    latitude   double precision,
    longitude  double precision,
    bright_ti4 real,
    scan       real,
    track      real,
    acq_date   date,
    acq_time   integer,
    satellite  varchar(20),
    instrument varchar(20),
    confidence varchar(10),
    version    varchar(10),
    bright_ti5 real,
    frp        real,
    daynight   char(1)
);

-- repeat for firms_viirs_noaa21_nrt, firms_viirs_snpp_nrt,
-- firms_modis_nrt, firms_goes_nrt (identical schema)

CREATE TABLE gdacs_live (
    id                integer,
    type              varchar(2),
    description       text,
    score             smallint,
    org_country       text,
    from_date         date,
    to_date           date,
    date_modified     timestamp,
    affectedcountries text,
    severity          double precision,
    severitytext      text,
    severityunit      varchar(10),
    iscurrent         boolean,
    geom_url          text,
    report_url        text,
    geometry          jsonb,
    CONSTRAINT gdacs_unique UNIQUE (id)
);
```

### 4. Run the API

```bash
uvicorn backend.main:app --reload
```

API available at `http://127.0.0.1:8000`. Docs at `http://127.0.0.1:8000/docs`.

### 5. Run the ingestion scripts

Each script accepts `--once` to run a single cycle and exit (used by GitHub Actions), or runs as a continuous loop by default. Open three terminals:

```bash
python backend/ingestion/ins_eq.py
```

```bash
python backend/ingestion/ins_fires.py
```

```bash
python backend/ingestion/ins_gdacs.py
```

### 6. Serve the frontend

```bash
python -m http.server 5500 --directory frontend
```

Open `http://localhost:5500`.

---

## Deployment

- **API:** Render web service (Docker, free tier)
- **Ingestion:** GitHub Actions cron every 30 minutes (`.github/workflows/ingest.yml`)
- **Database:** Supabase PostgreSQL -> use the session pooler host on port `5432` for Render compatibility
- **Frontend:** Render static site

Add the following secrets to your GitHub repo under **Settings > Secrets and variables > Actions**:

| Secret | Description |
|--------|-------------|
| `DB_HOST` | Supabase session pooler host |
| `DB_PORT` | `5432` |
| `DB_NAME` | `postgres` |
| `DB_USER` | `postgres.[project-ref]` |
| `DB_PASS` | Supabase password |
| `MAP_KEY` | NASA FIRMS API key |

---

## Roadmap

- Global coverage -> expand bounding boxes beyond Asia
- Volcano pipeline -> USGS Volcano Hazards or Smithsonian GVP
- Historical analytics -> query the archive table, show event frequency over time
- Alert severity overlay -> GDACS alert level (green/orange/red) encoded in marker color
- REST API pagination -> large earthquake archive responses need cursor-based pagination
- Data analysis export -> re-add the GDACS raw JSON dump for offline analysis

---

## Data sources

| Source | Provider | Update frequency |
|--------|----------|-----------------|
| [FIRMS NRT Fire Data](https://firms.modaps.eosdis.nasa.gov/) | NASA | ~10 minutes |
| [Earthquake Catalog](https://earthquake.usgs.gov/fdsnws/event/1/) | USGS | ~1 minute |
| [Global Disaster Alerts](https://www.gdacs.org/) | GDACS / EC JRC | ~15 minutes |

---

## Built by

**Zala Vishmayraj** - [GitHub](https://github.com/Vishmayraj) · [Instagram](https://www.instagram.com/notsoteekhipanipuri/) · [LinkedIn](https://www.linkedin.com/in/vishmayraj-zala-121018336/)