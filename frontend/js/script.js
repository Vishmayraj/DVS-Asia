// ===============================
// 🌍 Base Map Initialization
// ===============================
var map = L.map('map').setView([20, 80], 3);

L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; <a href="https://carto.com/">Carto</a>, &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors'
}).addTo(map);

// ===============================
// 🔹 Layers (placeholders)
// ===============================
let layers = {
  earthquakes: L.layerGroup().addTo(map),
  fires: L.layerGroup(),
  gdacs: L.layerGroup()
};

// ===============================
// 🔹 Fetch Functions
// ===============================
const API_BASE = "http://127.0.0.1:8000"; // change to localhost for dev

async function loadEarthquakes(filter = "all") {
  const res = await fetch(`${API_BASE}/earthquakes`);
  const data = await res.json();
  layers.earthquakes.clearLayers();

  data.forEach(eq => {
    const mag = eq.mag || 0;

    // Apply filter
    if (filter === "mag5" && mag < 5) return;
    if (filter === "mag6" && mag < 6) return;

    const color = mag >= 6 ? "#ff3333" :
                  mag >= 5 ? "#ff884d" :
                  mag >= 4 ? "#ffcc66" :
                  "#aaffaa";

    const marker = L.circleMarker([eq.lat, eq.lng], {
      radius: mag * 2 || 4,
      color: color,
      weight: 1,
      fillOpacity: 0.8
    });

    marker.bindPopup(`
      <b>${eq.place}</b><br>
      Magnitude: ${mag}<br>
      Time: ${new Date(eq.time).toLocaleString()}
    `);

    marker.addTo(layers.earthquakes);
  });
}


async function loadFires(source = "goes") {
  // Dynamically build the endpoint
  const res = await fetch(`${API_BASE}/firms_fires/${source}`);
  const data = await res.json();
  layers.fires.clearLayers();

  data.forEach(fire => {
    const rect = L.rectangle([
      [fire.latitude - 0.05, fire.longitude - 0.05],
      [fire.latitude + 0.05, fire.longitude + 0.05]
    ], { color: "orange", weight: 1, fillOpacity: 0.5 });

    rect.bindPopup(`🔥 Fire detected<br>${fire.confidence}% confidence`);
    rect.addTo(layers.fires);
  });
}

async function loadGDACS() {
  const res = await fetch(`${API_BASE}/gdacs`);
  const data = await res.json();
  layers.gdacs.clearLayers();

  data.forEach(event => {
    const marker = L.circleMarker([event.lat, event.lng], {
      radius: 8,
      color: "blue",
      fillOpacity: 0.7
    }).bindPopup(`
      <b>${event.description}</b><br>
      Severity: ${event.severitytext}
    `);
    marker.addTo(layers.gdacs);
  });
}

// ===============================
// 🔹 Dropdown Control (top-right)
// ===============================
var DataSelector = L.Control.extend({
  options: { position: 'topright' },

  onAdd: function() {
    const container = L.DomUtil.create('div', 'data-dropdown leaflet-bar');
    container.style.background = 'white';
    container.style.padding = '6px';
    container.style.borderRadius = '6px';
    container.style.display = 'flex';
    container.style.flexDirection = 'column';
    container.style.gap = '4px';

    // Main select
    const mainSelect = L.DomUtil.create('select', '', container);
    mainSelect.innerHTML = `
      <option value="none" selected>-- Select Data --</option>
      <option value="earthquakes">🌋 Earthquakes</option>
      <option value="fires">🔥 Fires</option>
      <option value="gdacs">🌀 GDACS Alerts</option>
    `;

    // Sub-select (hidden by default)
    const subSelect = L.DomUtil.create('select', '', container);
    subSelect.style.display = 'none';

    // Stop map interactions when interacting with controls
    [mainSelect, subSelect].forEach(el => {
      el.onmousedown = L.DomEvent.stopPropagation;
      el.ontouchstart = L.DomEvent.stopPropagation;
    });

    mainSelect.addEventListener('change', async (e) => {
      const choice = e.target.value;

      // Remove all layers first
      Object.values(layers).forEach(l => map.removeLayer(l));

      // Configure subSelect based on choice
      if (choice === "earthquakes") {
        subSelect.style.display = 'block';
        subSelect.innerHTML = `
          <option value="all" selected>All Magnitudes</option>
          <option value="mag5">Magnitude ≥ 5</option>
          <option value="mag6">Magnitude ≥ 6</option>
        `;
        // Load default
        await loadEarthquakes();
        map.addLayer(layers.earthquakes);

      } else if (choice === "fires") {
        subSelect.style.display = 'block';
        subSelect.innerHTML = `
          <option value="goes" selected>GOES</option>
          <option value="modis">MODIS</option>
          <option value="noaa20">NOAA20</option>
          <option value="noaa21">NOAA21</option>
          <option value="snpp">SNPP</option>
        `;
        await loadFires('goes'); // default source
        map.addLayer(layers.fires);

      } else if (choice === "gdacs") {
        subSelect.style.display = 'none';
        await loadGDACS();
        map.addLayer(layers.gdacs);
      } else {
        subSelect.style.display = 'none';
      }
    });

    subSelect.addEventListener('change', async (e) => {
      const mainChoice = mainSelect.value;
      const subChoice = e.target.value;

      Object.values(layers).forEach(l => map.removeLayer(l));

      if (mainChoice === "earthquakes") {
        await loadEarthquakes(subChoice); // pass mag filter
        map.addLayer(layers.earthquakes);
      } else if (mainChoice === "fires") {
        await loadFires(subChoice); // pass source
        map.addLayer(layers.fires);
      }
    });

    return container;
  }
});

map.addControl(new DataSelector());
