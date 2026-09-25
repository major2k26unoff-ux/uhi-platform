// Centre on India
const map = L.map('map').setView([21.0, 79.0], 5);

L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
  attribution: 'Tiles &copy; Esri',
  maxZoom: 19
}).addTo(map);

console.log('Map ready');

// Layer that holds whatever the user draws
const drawnItems = new L.FeatureGroup();
map.addLayer(drawnItems);

const drawControl = new L.Control.Draw({
  draw: {
    rectangle: true,
    polygon: false,
    circle: false,
    marker: false,
    polyline: false,
    circlemarker: false
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
    south: b.getSouth(),
    west: b.getWest(),
    north: b.getNorth(),
    east: b.getEast()
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