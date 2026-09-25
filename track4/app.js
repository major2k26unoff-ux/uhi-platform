// Centre on India
const map = L.map('map').setView([21.0, 79.0], 5);

L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
  attribution: 'Tiles &copy; Esri',
  maxZoom: 19
}).addTo(map);

console.log('Map ready');

// Drawing
const drawnItems = new L.FeatureGroup();
map.addLayer(drawnItems);

const drawControl = new L.Control.Draw({
  draw: {
    rectangle: true, polygon: false, circle: false,
    marker: false, polyline: false, circlemarker: false
  },
  edit: { featureGroup: drawnItems }
});
map.addControl(drawControl);

let currentAOI = null;

map.on(L.Draw.Event.CREATED, function (event) {
  drawnItems.clearLayers();
  drawnItems.addLayer(event.layer);
  const b = event.layer.getBounds();
  currentAOI = {
    south: b.getSouth(), west: b.getWest(),
    north: b.getNorth(), east: b.getEast()
  };
  console.log('AOI selected:', currentAOI);
  showAOIInfo(currentAOI);
});

function showAOIInfo(aoi) {
  const heightKm = (aoi.north - aoi.south) * 111;
  const widthKm = (aoi.east - aoi.west) * 105;
  document.getElementById('info-panel').innerHTML = `
    <strong>Selected area</strong><br>
    South ${aoi.south.toFixed(4)}<br>
    West ${aoi.west.toFixed(4)}<br>
    North ${aoi.north.toFixed(4)}<br>
    East ${aoi.east.toFixed(4)}<br>
    <em>About ${widthKm.toFixed(1)} by ${heightKm.toFixed(1)} km</em>
  `;
}

// Image overlay
let currentOverlay = null;
function showLayer(imageUrl, bounds) {
  if (currentOverlay) map.removeLayer(currentOverlay);
  currentOverlay = L.imageOverlay(imageUrl, bounds, {
    opacity: 0.75, interactive: false
  }).addTo(map);
  map.fitBounds(bounds);
}

// City presets (Day 5 will overwrite these from the server)
const CITY_BOUNDS = {
  bhubaneswar: [[20.20, 85.75], [20.35, 85.90]],
  delhi: [[28.50, 77.05], [28.75, 77.35]],
  phalodi: [[27.08, 72.30], [27.18, 72.42]],
  titlagarh: [[20.26, 83.09], [20.36, 83.21]]
};

let currentCity = 'bhubaneswar';
let currentLayer = 'rgb';

// Local placeholder image while Track 3's server is not yet wired in
const PLACEHOLDER_IMG = 'https://picsum.photos/id/28/400/400';

function refresh() {
  const url = PLACEHOLDER_IMG; // Day 5 replaces this with Track 3's URL
  showLayer(url, CITY_BOUNDS[currentCity]);
  updateLegend(currentLayer);
}

document.querySelectorAll('.layer-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.layer-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentLayer = btn.dataset.layer;
    refresh();
  });
});

document.getElementById('city-select').addEventListener('change', e => {
  currentCity = e.target.value;
  refresh();
});

// Legends
const LEGENDS = {
  lst: {
    title: 'Ground temperature',
    items: [['#fcffa4', '45 C and above'], ['#f98e09', '38 C'],
      ['#bc3754', '33 C'], ['#57106e', '28 C'], ['#000004', '25 C and below']]
  },
  ndvi: {
    title: 'Vegetation health',
    items: [['#1a9850', 'Dense healthy plants'], ['#d9ef8b', 'Sparse plants'],
      ['#fee08b', 'Bare ground'], ['#d73027', 'No vegetation']]
  },
  landcover: {
    title: 'Land cover',
    items: [['#397D49', 'Trees'], ['#88B053', 'Grass'],
      ['#C4281B', 'Buildings and roads'], ['#419BDF', 'Water'], ['#A59B8F', 'Bare soil']]
  },
  priority: {
    title: 'Planting priority',
    items: [['#67000d', 'Highest benefit'], ['#ef3b2c', 'High'],
      ['#fc9272', 'Medium'], ['#fee0d2', 'Low']]
  },
  rgb: { title: 'True colour satellite view', items: [] }
};

function updateLegend(layer) {
  const legend = LEGENDS[layer];
  const rows = legend.items.map(([colour, label]) =>
    `<div class="legend-row"><span class="swatch" style="background:${colour}"></span>${label}</div>`
  ).join('');
  document.getElementById('legend').innerHTML = `<strong>${legend.title}</strong>${rows}`;
}

// Kick things off
refresh();