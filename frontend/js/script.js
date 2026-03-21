const API_BASE = "http://127.0.0.1:8000";

// ── MAP INIT ─────────────────────────────────────────────

var map = L.map("map", {
    minZoom: 3,
    maxZoom: 14,
    zoomControl: true,
}).setView([22, 90], 4);

var tileDark = L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    { attribution: '&copy; <a href="https://carto.com/">Carto</a> &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>' }
);

var tileLight = L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    { attribution: '&copy; <a href="https://carto.com/">Carto</a> &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>' }
);

tileDark.addTo(map);

// ── LAYERS ───────────────────────────────────────────────

let layers = {
    earthquakes: L.layerGroup().addTo(map),
    fires:       L.layerGroup(),
};

// ── STATE ────────────────────────────────────────────────

let state = {
    source:     "earthquakes",
    magFilter:  "all",
    satFilter:  "goes",
    eqData:     [],
    fireData:   [],
    theme:      "dark",
};

// ── THEME ────────────────────────────────────────────────

function toggleTheme() {
    state.theme = state.theme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", state.theme);
    document.getElementById("theme-icon").textContent = state.theme === "dark" ? "☀" : "☾";

    if (state.theme === "dark") {
        map.removeLayer(tileLight);
        tileDark.addTo(map);
    } else {
        map.removeLayer(tileDark);
        tileLight.addTo(map);
    }
}

// ── MOBILE SHEET ─────────────────────────────────────────

function toggleSheet() {
    const sidebar = document.getElementById("sidebar");
    const label   = document.getElementById("sheet-label");
    const open    = sidebar.classList.toggle("sheet-open");
    label.textContent = open ? "Hide panel" : "Show panel";
}

// ── HELPERS ──────────────────────────────────────────────

function magColor(mag) {
    if (mag >= 7)  return "#ff1a1a";
    if (mag >= 6)  return "#f87171";
    if (mag >= 5)  return "#fb923c";
    if (mag >= 4)  return "#facc15";
    return "#22d3b8";
}

function magRadius(mag) {
    return Math.max(2, (mag || 0) * 1.5);
}

function formatTime(iso) {
    return new Date(iso).toUTCString();
}

function setLastUpdated() {
    document.getElementById("last-updated").textContent =
        "Updated " + new Date().toLocaleTimeString();
}

function setStats(total, visible) {
    document.getElementById("stat-count").textContent   = total.toLocaleString();
    document.getElementById("stat-visible").textContent = visible.toLocaleString();
}

function showError(msg) {
    const el = document.getElementById("map-error");
    el.textContent = msg;
    el.style.display = "block";
    setTimeout(() => el.style.display = "none", 5000);
}

// ── SOURCE SELECTOR ───────────────────────────────────────

function selectSource(src) {
    if (src === "gdacs") return;

    state.source = src;

    document.querySelectorAll(".source-btn").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.source === src);
    });

    document.getElementById("filter-earthquakes").classList.toggle("hidden", src !== "earthquakes");
    document.getElementById("filter-fires").classList.toggle("hidden", src !== "fires");
    document.getElementById("legend-earthquakes").classList.toggle("hidden", src !== "earthquakes");
    document.getElementById("legend-fires").classList.toggle("hidden", src !== "fires");
    document.getElementById("legend-gdacs").classList.toggle("hidden", src !== "gdacs");

    Object.values(layers).forEach(l => map.removeLayer(l));

    if (src === "earthquakes") {
        map.addLayer(layers.earthquakes);
        loadEarthquakes(state.magFilter);
    } else if (src === "fires") {
        map.addLayer(layers.fires);
        loadFires(state.satFilter);
    }
}

// ── MAG FILTER ────────────────────────────────────────────

function setMagFilter(f) {
    state.magFilter = f;
    document.querySelectorAll(".pill[data-mag]").forEach(p => {
        p.classList.toggle("active", p.dataset.mag === f);
    });
    renderEarthquakes();
}

// ── SAT FILTER ────────────────────────────────────────────

function setSatFilter(s) {
    state.satFilter = s;
    document.querySelectorAll(".pill[data-sat]").forEach(p => {
        p.classList.toggle("active", p.dataset.sat === s);
    });
    loadFires(s);
}

// ── EARTHQUAKES ───────────────────────────────────────────

async function loadEarthquakes() {
    try {
        const res = await fetch(`${API_BASE}/earthquakes`);
        if (!res.ok) throw new Error(`Server returned ${res.status}`);
        state.eqData = await res.json();
        setLastUpdated();
        renderEarthquakes();
    } catch (err) {
        showError(`Earthquakes: ${err.message}`);
    }
}

function renderEarthquakes() {
    layers.earthquakes.clearLayers();
    const f = state.magFilter;
    let visible = 0;

    state.eqData.forEach(eq => {
        const mag = eq.mag || 0;
        if (f === "mag7" && mag < 7) return;
        if (f === "mag6" && mag < 6) return;
        if (f === "mag5" && mag < 5) return;

        visible++;

        const marker = L.circleMarker([eq.lat, eq.lng], {
            radius:      magRadius(mag),
            color:       magColor(mag),
            fillColor:   magColor(mag),
            weight:      1,
            fillOpacity: 0.8,
        });

        marker.bindTooltip(
            `<b>${eq.place}</b><br>M${mag} &nbsp;·&nbsp; ${formatTime(eq.time)}`,
            { sticky: true }
        );

        marker.bindPopup(`
            <div class="dvs-popup">
                <div class="dvs-popup-title">${eq.place}</div>
                <table class="dvs-popup-table">
                    <tr>
                        <td>Magnitude</td>
                        <td><span class="popup-mag">M${mag}</span> &nbsp;<span style="color:var(--text-3);font-size:0.7rem">${eq.magtype || "—"}</span></td>
                    </tr>
                    <tr>
                        <td>Depth</td>
                        <td>${eq.depth != null ? eq.depth.toFixed(1) + " km" : "—"}</td>
                    </tr>
                    <tr>
                        <td>Tsunami</td>
                        <td>${eq.tsunami ? '<span class="popup-warn">⚠ Warning issued</span>' : "None"}</td>
                    </tr>
                    <tr>
                        <td>Significance</td>
                        <td>${eq.sig ?? "—"}</td>
                    </tr>
                    <tr>
                        <td>Time (UTC)</td>
                        <td>${formatTime(eq.time)}</td>
                    </tr>
                    <tr>
                        <td>ID</td>
                        <td style="color:var(--text-3);font-size:0.7rem">${eq.id}</td>
                    </tr>
                </table>
            </div>
        `);

        marker.addTo(layers.earthquakes);
    });

    setStats(state.eqData.length, visible);
}

// ── FIRES (stub) ──────────────────────────────────────────

async function loadFires(source = "goes") {
    try {
        const res = await fetch(`${API_BASE}/firms_fires?source=${source}`);
        if (!res.ok) throw new Error(`Server returned ${res.status}`);
        state.fireData = await res.json();
        setLastUpdated();
        renderFires();
    } catch (err) {
        showError(`Fires: ${err.message}`);
    }
}

function renderFires() {
    layers.fires.clearLayers();
    let visible = 0;

    state.fireData.forEach(fire => {
        visible++;
        const rect = L.rectangle([
            [fire.lat - 0.05, fire.lng - 0.05],
            [fire.lat + 0.05, fire.lng + 0.05]
        ], { color: "#fb923c", weight: 0.5, fillOpacity: 0.55 });

        rect.bindTooltip(`Fire detected · ${fire.confidence}% confidence`, { sticky: true });
        rect.addTo(layers.fires);
    });

    setStats(state.fireData.length, visible);
}

// ── INITIAL LOAD ──────────────────────────────────────────

loadEarthquakes();