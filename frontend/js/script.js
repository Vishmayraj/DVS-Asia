const API_BASE = "http://127.0.0.1:8000";

var map = L.map("map").setView([20, 90], 4);

L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://carto.com/">Carto</a>, &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors'
}).addTo(map);

let layers = {
    earthquakes: L.layerGroup().addTo(map),
    fires: L.layerGroup(),
};

// ---- helpers ----

function magColor(mag) {
    if (mag >= 7)   return "#ff1a1a";
    if (mag >= 6)   return "#ff6600";
    if (mag >= 5)   return "#ffaa00";
    if (mag >= 4)   return "#ffee00";
    return "#aaffaa";
}

function magRadius(mag) {
    return Math.max(2, (mag || 0) * 1.5);
}

function formatTime(isoString) {
    return new Date(isoString).toUTCString();
}

function showError(message) {
    console.error(message);
    const el = document.getElementById("map-error");
    if (el) {
        el.textContent = message;
        el.style.display = "block";
        setTimeout(() => el.style.display = "none", 5000);
    }
}

// ---- earthquakes ----

async function loadEarthquakes(magFilter = "all") {
    try {
        const res = await fetch(`${API_BASE}/earthquakes`);
        if (!res.ok) throw new Error(`Server returned ${res.status}`);
        const data = await res.json();

        layers.earthquakes.clearLayers();

        data.forEach(eq => {
            const mag = eq.mag || 0;

            if (magFilter === "mag7" && mag < 7) return;
            if (magFilter === "mag6" && mag < 6) return;
            if (magFilter === "mag5" && mag < 5) return;

            const marker = L.circleMarker([eq.lat, eq.lng], {
                radius:      magRadius(mag),
                color:       magColor(mag),
                fillColor:   magColor(mag),
                weight:      1,
                fillOpacity: 0.75,
            });

            // hover -> summary
            marker.bindTooltip(`
                <b>${eq.place}</b><br>
                M${mag} &nbsp;|&nbsp; ${formatTime(eq.time)}
            `, { sticky: true });

            // click -> full detail
            marker.bindPopup(`
                <div class="dvs-popup">
                    <div class="dvs-popup-title">${eq.place}</div>
                    <table class="dvs-popup-table">
                        <tr><td>Magnitude</td><td><b>${mag}</b> <span class="muted">(${eq.magtype || "—"})</span></td></tr>
                        <tr><td>Depth</td><td>${eq.depth != null ? eq.depth.toFixed(1) + " km" : "—"}</td></tr>
                        <tr><td>Tsunami</td><td>${eq.tsunami ? "⚠ Warning issued" : "None"}</td></tr>
                        <tr><td>Significance</td><td>${eq.sig ?? "—"}</td></tr>
                        <tr><td>Time (UTC)</td><td>${formatTime(eq.time)}</td></tr>
                        <tr><td>ID</td><td><span class="muted">${eq.id}</span></td></tr>
                    </table>
                </div>
            `);

            marker.addTo(layers.earthquakes);
        });

    } catch (err) {
        showError(`Failed to load earthquakes: ${err.message}`);
    }
}

// ---- fires (stub — fields to be decided) ----

async function loadFires(source = "goes") {
    try {
        const res = await fetch(`${API_BASE}/firms_fires?source=${source}`);
        if (!res.ok) throw new Error(`Server returned ${res.status}`);
        const data = await res.json();

        layers.fires.clearLayers();

        data.forEach(fire => {
            const rect = L.rectangle([
                [fire.lat - 0.05, fire.lng - 0.05],
                [fire.lat + 0.05, fire.lng + 0.05]
            ], { color: "orange", weight: 1, fillOpacity: 0.5 });

            rect.bindTooltip(`🔥 ${fire.confidence}% confidence`, { sticky: true });
            rect.addTo(layers.fires);
        });

    } catch (err) {
        showError(`Failed to load fires: ${err.message}`);
    }
}

// ---- dropdown control ----

var DataSelector = L.Control.extend({
    options: { position: "topright" },

    onAdd: function () {
        const container = L.DomUtil.create("div", "dvs-control leaflet-bar");

        const mainSelect = L.DomUtil.create("select", "dvs-select", container);
        mainSelect.innerHTML = `
            <option value="none" selected>-- Select data --</option>
            <option value="earthquakes">Earthquakes</option>
            <option value="fires">Fires</option>
        `;

        const subSelect = L.DomUtil.create("select", "dvs-select", container);
        subSelect.style.display = "none";

        [mainSelect, subSelect].forEach(el => {
            L.DomEvent.disableClickPropagation(el);
            L.DomEvent.disableScrollPropagation(el);
        });

        mainSelect.addEventListener("change", async (e) => {
            const choice = e.target.value;
            Object.values(layers).forEach(l => map.removeLayer(l));

            if (choice === "earthquakes") {
                subSelect.style.display = "block";
                subSelect.innerHTML = `
                    <option value="all" selected>All magnitudes</option>
                    <option value="mag5">M5+</option>
                    <option value="mag6">M6+</option>
                    <option value="mag7">M7+</option>
                `;
                await loadEarthquakes("all");
                map.addLayer(layers.earthquakes);

            } else if (choice === "fires") {
                subSelect.style.display = "block";
                subSelect.innerHTML = `
                    <option value="goes"  selected>GOES</option>
                    <option value="modis">MODIS</option>
                    <option value="noaa20">NOAA-20</option>
                    <option value="noaa21">NOAA-21</option>
                    <option value="snpp">SNPP</option>
                `;
                await loadFires("goes");
                map.addLayer(layers.fires);

            } else {
                subSelect.style.display = "none";
            }
        });

        subSelect.addEventListener("change", async (e) => {
            const main  = mainSelect.value;
            const sub   = e.target.value;
            Object.values(layers).forEach(l => map.removeLayer(l));

            if (main === "earthquakes") {
                await loadEarthquakes(sub);
                map.addLayer(layers.earthquakes);
            } else if (main === "fires") {
                await loadFires(sub);
                map.addLayer(layers.fires);
            }
        });

        return container;
    }
});

map.addControl(new DataSelector());