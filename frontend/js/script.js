// Map initialization
var map = L.map('map').setView([43.6811, 87.3311], 4); // zoomed out more to see countries

// English-labelled basemap (Carto Light)
var carto = L.tileLayer(
  'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
  {
    attribution: '&copy; <a href="https://carto.com/">Carto</a>, &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors'
  }
);

// Add the English map
carto.addTo(map);