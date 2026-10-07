// ================================================================
// Urban Heat Island map - Week 2
// Talks to Track 3's API. Change API if the server address changes.
// ================================================================
const API = 'http://localhost:8000';
const POLL_MS = 3000;

// ---------- map ----------
const map = L.map('map').setView([21.0, 79.0], 5);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors', maxZoom: 19
}).addTo(map);

// ---------- what is on screen right now ----------
let currentSlug = null;
let currentMeta = null;
let currentBounds = null;
let currentLayer = 'rgb';
let currentOverlay = null;
let zonesLayer = null;
let currentAOI = null;

// ================================================================
// Day 1 - real data
// ================================================================
async function getJSON(path) {
  const res = await fetch(API + path);
  if (!res.ok) {
    let detail = 'Server returned ' + res.status;
    try {
      const body = await res.json();
      if (typeof body.detail === 'string') detail = body.detail;
    } catch (e) { /* not JSON */ }
    throw new Error(detail);
  }
  return res.json();
}

async function loadArea(slug) {
  try {
    const meta = await getJSON(`/api/results/${slug}`);
    currentSlug = slug;
    currentMeta = meta;
    const [s, w, n, e] = meta.bounds;
    currentBounds = [[s, w], [n, e]];
    map.fitBounds(currentBounds);
    updateLayerButtons();
    showCurrentLayer();
    showAreaInfo();
  } catch (err) {
    showMessage('Could not load this area', err.message);
  }
}

function showCurrentLayer() {
  if (currentOverlay) { map.removeLayer(currentOverlay); currentOverlay = null; }
  if (zonesLayer) { map.removeLayer(zonesLayer); zonesLayer = null; }
  updateLegend(currentLayer);
  if (!currentMeta) return;

  const path = currentMeta.layer_urls[currentLayer];
  if (!path) {
    showMessage('Layer not ready', 'This layer has not been produced for this area yet.');
    return;
  }
  currentOverlay = L.imageOverlay(API + path, currentBounds, { opacity: 0.8 }).addTo(map);

  if (currentLayer === 'priority') showZones();
}

function updateLayerButtons() {
  document.querySelectorAll('.layer-btn').forEach(btn => {
    btn.disabled = !(currentMeta && currentMeta.layer_urls[btn.dataset.layer]);
  });
}

// ================================================================
// Day 2 - city list and statistics
// ================================================================
async function loadCities() {
  const select = document.getElementById('city-select');
  try {
    const data = await getJSON('/api/cities');
    select.innerHTML = '<option value="">Choose a city…</option>';
    const groups = { metro: 'Major cities', hot_town: 'Extreme-heat towns' };
    for (const [key, label] of Object.entries(groups)) {
      const group = document.createElement('optgroup');
      group.label = label;
      data.cities.filter(c => c.group === key).forEach(city => {
        const option = document.createElement('option');
        option.value = city.slug;
        option.textContent = city.ready ? city.name : `${city.name} (not processed yet)`;
        option.disabled = !city.ready;
        group.appendChild(option);
      });
      select.appendChild(group);
    }
    const first = data.cities.find(c => c.ready);
    if (first) { select.value = first.slug; loadArea(first.slug); }
    else showMessage('No cities processed yet', 'Draw a box and click Analyze to start.');
  } catch (err) {
    showMessage('Server not reachable', `Is Track 3's server running at ${API}?`);
  }
}

const r1 = x => Number(x).toFixed(1);
const r2 = x => Number(x).toFixed(2);

function showAreaInfo(summary) {
  const st = currentMeta.stats;
  let html = `
    <h3>${currentMeta.display_name}</h3>
    Ground temperature: <strong>${r1(st.lst_mean_c)} °C</strong> average<br>
    Range ${r1(st.lst_min_c)} – ${r1(st.lst_max_c)} °C<br>
    Greenness (NDVI): ${r2(st.ndvi_mean)}<br>`;
  if (currentMeta.date_start) {
    html += `<span class="muted">Satellite dates ${currentMeta.date_start} to ${currentMeta.date_end}</span>`;
  }
  if (summary) {
    body.push(el('div', { class: 'cooling' },
      el('p', { class: 'cooling-label' }, `Top ${summary.top_zones} planting zones would cool by`),
      el('p', { class: 'cooling-value' }, `${r2(summary.delta_t.top_mean_c)} °C`),
      el('p', { class: 'muted' },
        `On average, up to ${r2(summary.delta_t.top_max_c)} °C. Scenario: up to 20% more tree cover ` +
        'per 100 m block, estimated from this area\'s own data. A planning guide, not a guarantee.')));
  }
  document.getElementById('info-panel').innerHTML = html;
}

function showMessage(title, text) {
  document.getElementById('info-panel').innerHTML = `<h3>${title}</h3><p>${text}</p>`;
}

// ================================================================
// Day 3 - the "Plant here" layer
// ================================================================
const TIER_COLOURS = { 1: '#67000d', 2: '#cb181d', 3: '#fb6a4a', 4: '#fcbba1' };

async function showZones() {
  try {
    const [geo, summary] = await Promise.all([
      getJSON(`/api/priority/${currentSlug}`),
      getJSON(`/api/priority/${currentSlug}/summary`)
    ]);
    if (currentLayer !== 'priority') return;
    zonesLayer = L.geoJSON(geo, {
      style: f => ({ color: TIER_COLOURS[f.properties.tier], weight: 1.5, fillOpacity: 0.35 }),
      onEachFeature: (f, layer) => layer.bindPopup(zonePopup(f.properties))
    }).addTo(map);
    showAreaInfo(summary);
  } catch (err) {
    showMessage('No planting zones yet', 'Track 2 has not produced the priority map for this area.');
  }
}

function zonePopup(p) {
  return el('div', { class: 'zone-popup' },
    el('div', { class: 'zone-title' }, `Zone #${p.rank}, ${p.tier_label} priority`),
    'Expected cooling',
    el('span', { class: 'cool' }, `${p.delta_t_c} °C`),
    `Now ${p.lst_now_c} °C, after about ${p.lst_after_c} °C`, el('br'),
    `Tree cover ${p.tree_pct_now}% to ${p.tree_pct_after}%`, el('br'),
    `Built-up ${p.built_pct}%`);
}

const fmt = x => Number(x).toLocaleString('en-IN');

// ================================================================
// Day 4 - draw a box, analyze it, watch progress
// ================================================================
const drawnItems = new L.FeatureGroup();
map.addLayer(drawnItems);
map.addControl(new L.Control.Draw({
  draw: { rectangle: true, polygon: false, circle: false, marker: false,
          polyline: false, circlemarker: false },
  edit: { featureGroup: drawnItems }
}));

map.on(L.Draw.Event.CREATED, event => {
  drawnItems.clearLayers();
  drawnItems.addLayer(event.layer);
  const b = event.layer.getBounds();
  currentAOI = { south: b.getSouth(), west: b.getWest(), north: b.getNorth(), east: b.getEast() };
  const km = (deg, lat) => (deg * 111 * (lat ? Math.cos(lat * Math.PI / 180) : 1)).toFixed(1);
  document.getElementById('info-panel').innerHTML = `
    <h3>Selected area</h3>
    About ${km(currentAOI.east - currentAOI.west, currentAOI.south)} ×
    ${km(currentAOI.north - currentAOI.south)} km<br>
    <span class="muted">Processing takes a few minutes.</span><br>
    <button onclick="analyzeArea()">Analyze this area</button>`;
});

async function analyzeArea() {
  if (!currentAOI) return;
  showMessage('Analyzing…', 'You can move around the map while you wait.');
  setProgress(0, 'Sending request');
  try {
    const res = await fetch(API + '/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...currentAOI, name: 'Custom area' })
    });
    const body = await res.json();
    if (!res.ok) {
      hideProgress();
      showMessage('Cannot analyze this box',
        typeof body.detail === 'string' ? body.detail : 'The box coordinates were not accepted.');
      return;
    }
    watchJob(body.job_id);
  } catch (err) {
    hideProgress();
    showMessage('Server not reachable', `Is Track 3's server running at ${API}?`);
  }
}

function watchJob(jobId) {
  const timer = setInterval(async () => {
    try {
      const job = await getJSON(`/api/jobs/${jobId}`);
      setProgress(job.progress, job.stage);
      if (job.status === 'done') {
        clearInterval(timer);
        hideProgress();
        drawnItems.clearLayers();
        currentLayer = 'priority';
        setActiveButton('priority');
        loadArea(job.slug);
      } else if (job.status === 'failed') {
        clearInterval(timer);
        hideProgress();
        showMessage('Analysis failed', (job.error || 'Unknown error').split('\n')[0]);
      }
    } catch (err) {
      setProgress(null, 'Waiting for the server…');
    }
  }, POLL_MS);
}

function setProgress(pct, stage) {
  document.getElementById('progress').classList.remove('hidden');
  document.getElementById('progress-stage').textContent = stage;
  if (pct !== null) {
    document.getElementById('progress-bar').style.width = pct + '%';
    document.getElementById('progress-pct').textContent = pct + '%';
  }
}

function hideProgress() {
  document.getElementById('progress').classList.add('hidden');
}

// ================================================================
// Legend and buttons
// ================================================================
const LEGENDS = {
  rgb: { title: 'True-colour satellite view', items: [] },
  lst: { title: 'Ground temperature', items: [
    ['#fcffa4', '45 °C and above'], ['#f98e09', '40 °C'], ['#bc3754', '35 °C'],
    ['#57106e', '30 °C'], ['#000004', '25 °C and below']] },
  ndvi: { title: 'Vegetation health', items: [
    ['#1a9850', 'Dense healthy plants'], ['#d9ef8b', 'Sparse plants'],
    ['#fee08b', 'Bare ground'], ['#d73027', 'No vegetation']] },
  landcover: { title: 'Land cover', items: [
    ['#397D49', 'Trees'], ['#88B053', 'Grass'], ['#E49635', 'Crops'],
    ['#C4281B', 'Buildings and roads'], ['#419BDF', 'Water'], ['#A59B8F', 'Bare soil']] },
  priority: { title: 'Planting priority', items: [
    ['#67000d', 'Highest — top 10%'], ['#cb181d', 'High'],
    ['#fb6a4a', 'Medium'], ['#fcbba1', 'Low']] }
};

function updateLegend(layer) {
  const legend = LEGENDS[layer];
  const rows = legend.items.map(([colour, label]) =>
    `<div class="legend-row"><span class="swatch" style="background:${colour}"></span>${label}</div>`).join('');
  const hint = layer === 'priority' ? '<div class="muted" style="margin-top:6px">Click a zone for details</div>' : '';
  document.getElementById('legend').innerHTML = `<strong>${legend.title}</strong>${rows}${hint}`;
}

function setActiveButton(layer) {
  document.querySelectorAll('.layer-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.layer === layer));
}

document.querySelectorAll('.layer-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    currentLayer = btn.dataset.layer;
    setActiveButton(currentLayer);
    showCurrentLayer();
    if (currentMeta && currentLayer !== 'priority') showAreaInfo();
  });
});

document.getElementById('city-select').addEventListener('change', e => {
  if (e.target.value) loadArea(e.target.value);
});

// ---------- start ----------
updateLegend(currentLayer);
loadCities();