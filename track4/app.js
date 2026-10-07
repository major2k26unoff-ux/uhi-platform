// ================================================================
// Urban Heat Island map - Week 3 (map-first layout)
// Talks to Track 3's API. Change API if the server address changes.
// ================================================================
const API = 'http://localhost:8000';
const POLL_MS = 3000;
const DEFAULT_OPACITY = 0.6;
const PHONE = window.matchMedia('(max-width: 700px)');

const $ = id => document.getElementById(id);

// ---------- map ----------
const map = L.map('map', { zoomControl: false }).setView([21.0, 79.0], 5);
L.control.zoom({ position: 'topright' }).addTo(map);
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
let overlayOpacity = DEFAULT_OPACITY;
let jobRunning = false;

// Small DOM builder. Strings become text nodes, so API values never become HTML.
function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === 'class') node.className = value;
    else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value);
  }
  node.append(...children.flat().filter(c => c !== null && c !== undefined && c !== false));
  return node;
}

// ================================================================
// Talking to the API
// ================================================================
async function getJSON(path) {
  let res;
  try {
    res = await fetch(API + path);
  } catch (e) {
    const err = new Error('Server not reachable');
    err.offline = true;
    throw err;
  }
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

function showServerDown() {
  showMessage('Server not reachable',
    `Start Track 3's server at ${API}, then reload this page.`, 'error');
}

// ================================================================
// Areas and layers
// ================================================================
async function loadArea(slug) {
  setInfo('Loading…', [el('p', { class: 'muted' }, 'Fetching layers and statistics.')], { tone: 'loading' });
  try {
    const meta = await getJSON(`/api/results/${slug}`);
    currentSlug = slug;
    currentMeta = meta;
    const [s, w, n, e] = meta.bounds;
    currentBounds = [[s, w], [n, e]];
    map.fitBounds(currentBounds);
    // ponytail: only falls back when the chosen layer does not exist for this area
    if (!meta.layer_urls[currentLayer]) currentLayer = 'rgb';
    setActiveButton(currentLayer);
    updateLayerButtons();
    if (showCurrentLayer()) showAreaInfo();
  } catch (err) {
    if (err.offline) showServerDown();
    else showMessage('Could not load this area', err.message, 'error');
  }
}

// Draws the chosen layer. Returns false when the layer is missing for this area.
function showCurrentLayer() {
  if (currentOverlay) { map.removeLayer(currentOverlay); currentOverlay = null; }
  if (zonesLayer) { map.removeLayer(zonesLayer); zonesLayer = null; }
  updateLegend(currentLayer);
  if (!currentMeta) return false;

  const path = currentMeta.layer_urls[currentLayer];
  if (!path) {
    showMessage('Not processed yet',
      `The ${layerName(currentLayer)} layer has not been produced for this area yet.`, 'empty');
    return false;
  }
  currentOverlay = L.imageOverlay(API + path, currentBounds, { opacity: overlayOpacity }).addTo(map);
  if (currentLayer === 'priority') showZones();
  return true;
}

function updateLayerButtons() {
  document.querySelectorAll('.layer-btn').forEach(btn => {
    btn.disabled = !(currentMeta && currentMeta.layer_urls[btn.dataset.layer]);
  });
}

function layerName(layer) {
  return document.querySelector(`.layer-btn[data-layer="${layer}"]`).textContent;
}

// ================================================================
// City list and statistics
// ================================================================
async function loadCities() {
  const select = $('city-select');
  try {
    const data = await getJSON('/api/cities');
    select.replaceChildren(el('option', { value: '' }, 'Choose a city…'));
    const groups = { metro: 'Major cities', hot_town: 'Extreme-heat towns' };
    for (const [key, label] of Object.entries(groups)) {
      const group = el('optgroup', { label });
      data.cities.filter(c => c.group === key).forEach(city => {
        const option = el('option', { value: city.slug },
          city.ready ? city.name : `${city.name} (not processed yet)`);
        option.disabled = !city.ready;
        group.append(option);
      });
      select.append(group);
    }
    const first = data.cities.find(c => c.ready);
    if (first) { select.value = first.slug; loadArea(first.slug); }
    else showMessage('No cities processed yet', 'Draw a box with the square tool, then press Analyze.', 'empty');
  } catch (err) {
    select.replaceChildren(el('option', { value: '' }, 'Server not reachable'));
    showServerDown();
  }
}

const r1 = x => Number(x).toFixed(1);
const r2 = x => Number(x).toFixed(2);

function stat(label, value, lead = false) {
  return el('div', { class: lead ? 'stat stat-lead' : 'stat' },
    el('span', { class: 'stat-label' }, label),
    el('span', { class: 'stat-value' }, value));
}

function showAreaInfo(summary) {
  const st = currentMeta.stats;
  const body = [
    stat('Average ground temperature', `${r1(st.lst_mean_c)} °C`, true),
    stat('Range', `${r1(st.lst_min_c)} to ${r1(st.lst_max_c)} °C`),
    stat('Greenness (NDVI)', r2(st.ndvi_mean)),
    currentMeta.date_start &&
      el('p', { class: 'muted' }, `Satellite dates ${currentMeta.date_start} to ${currentMeta.date_end}`)
  ];
  if (summary) {
    body.push(el('div', { class: 'cooling' },
      el('p', { class: 'cooling-label' }, `Top ${summary.top_zones} planting zones would cool by`),
      el('p', { class: 'cooling-value' }, `${r2(summary.delta_t.top_mean_c)} °C`),
      el('p', { class: 'muted' },
        `On average, up to ${r2(summary.delta_t.top_max_c)} °C. Scenario: up to 20% more tree cover ` +
        'per 100 m block, estimated from this area\'s own data. A planning guide, not a guarantee.')));
  }
  setInfo(currentMeta.display_name, body);
}

// tone: '' | 'loading' | 'empty' | 'error'
function setInfo(title, body = [], { tone = '', open = false } = {}) {
  $('info-title').textContent = title;
  $('info-body').replaceChildren(...body.filter(Boolean));
  $('info-card').dataset.tone = tone;
  if (open || tone === 'error') $('info-card').open = true;
}

function showMessage(title, text, tone = '') {
  setInfo(title, [el('p', {}, text)], { tone });
}

// ================================================================
// The "Plant here" layer
// ================================================================
const TIER_COLOURS = { 1: '#67000d', 2: '#cb181d', 3: '#fb6a4a', 4: '#fcbba1' };

async function showZones() {
  const slug = currentSlug;
  try {
    const [geo, summary] = await Promise.all([
      getJSON(`/api/priority/${slug}`),
      getJSON(`/api/priority/${slug}/summary`)
    ]);
    if (currentLayer !== 'priority' || slug !== currentSlug) return;
    zonesLayer = L.geoJSON(geo, {
      style: f => ({ color: TIER_COLOURS[f.properties.tier], weight: 1.5, fillOpacity: 0.35 }),
      onEachFeature: (f, layer) => layer.bindPopup(() => zonePopup(f.properties), {
        // keep popups clear of the floating cards at the top
        autoPanPaddingTopLeft: [16, $('top-ui').offsetHeight + 24]
      })
    }).addTo(map);
    showAreaInfo(summary);
  } catch (err) {
    if (err.offline) showServerDown();
    else showMessage('Not processed yet', 'Track 2 has not produced the planting zones for this area.', 'empty');
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

// ================================================================
// Draw a box, analyze it, watch progress
// ================================================================
const drawnItems = new L.FeatureGroup();
map.addLayer(drawnItems);
map.addControl(new L.Control.Draw({
  position: 'topright',
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
  setInfo('Custom area selected', [
    el('p', {}, `About ${km(currentAOI.east - currentAOI.west, currentAOI.south)} × ` +
      `${km(currentAOI.north - currentAOI.south)} km`),
    el('p', { class: 'muted' }, 'Processing takes a few minutes. You can keep exploring the map while it runs.'),
    el('button', { type: 'button', class: 'btn-primary', onclick: analyzeArea }, 'Analyze this area')
  ], { open: true });
});

async function analyzeArea() {
  if (!currentAOI || jobRunning) return;
  jobRunning = true;
  showMessage('Analyzing…', 'You can move around the map while you wait.', 'loading');
  setProgress(0, 'Sending request');
  try {
    const res = await fetch(API + '/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...currentAOI, name: 'Custom area' })
    });
    const body = await res.json();
    if (!res.ok) {
      finishJob();
      showMessage('Cannot analyze this box',
        typeof body.detail === 'string' ? body.detail : 'The box coordinates were not accepted. Draw a smaller box inside India.',
        'error');
      return;
    }
    watchJob(body.job_id);
  } catch (err) {
    finishJob();
    showServerDown();
  }
}

function watchJob(jobId) {
  const timer = setInterval(async () => {
    try {
      const job = await getJSON(`/api/jobs/${jobId}`);
      setProgress(job.progress, job.stage);
      if (job.status === 'done') {
        clearInterval(timer);
        finishJob();
        drawnItems.clearLayers();
        $('city-select').value = '';
        loadArea(job.slug); // keeps whichever layer the user had chosen
      } else if (job.status === 'failed') {
        clearInterval(timer);
        finishJob();
        showMessage('Analysis failed', (job.error || 'Unknown error').split('\n')[0], 'error');
      }
    } catch (err) {
      setProgress(null, 'Waiting for the server…');
    }
  }, POLL_MS);
}

function setProgress(pct, stage) {
  $('progress').hidden = false;
  $('progress-stage').textContent = stage;
  if (pct !== null && pct !== undefined) {
    $('progress-bar').style.transform = `scaleX(${pct / 100})`;
    $('progress-pct').textContent = pct + '%';
  }
}

function finishJob() {
  jobRunning = false;
  $('progress').hidden = true;
}

// ================================================================
// Legend, opacity and layer buttons
// ================================================================
const LEGENDS = {
  rgb: { title: 'True-colour satellite view', items: [],
         note: 'The area as a camera sees it from orbit.' },
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
    ['#67000d', 'Highest (top 10%)'], ['#cb181d', 'High'],
    ['#fb6a4a', 'Medium'], ['#fcbba1', 'Low']],
    note: 'Click a zone for its expected cooling.' }
};

function updateLegend(layer) {
  const legend = LEGENDS[layer];
  $('active-layer-name').textContent = layerName(layer);
  $('legend-title').textContent = legend.title;
  $('legend-rows').replaceChildren(...legend.items.map(([colour, label]) => {
    const swatch = el('span', { class: 'swatch', 'aria-hidden': 'true' });
    swatch.style.background = colour;
    return el('div', { class: 'legend-row' }, swatch, label);
  }));
  $('legend-note').textContent = legend.note || '';
}

function setActiveButton(layer) {
  document.querySelectorAll('.layer-btn').forEach(b => {
    const on = b.dataset.layer === layer;
    b.classList.toggle('active', on);
    b.setAttribute('aria-pressed', String(on));
  });
}

document.querySelectorAll('.layer-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    currentLayer = btn.dataset.layer;
    setActiveButton(currentLayer);
    if (showCurrentLayer()) showAreaInfo();
  });
});

$('opacity').addEventListener('input', e => {
  overlayOpacity = Number(e.target.value) / 100;
  $('opacity-value').textContent = e.target.value + '%';
  if (currentOverlay) currentOverlay.setOpacity(overlayOpacity);
});

$('city-select').addEventListener('change', e => {
  if (e.target.value) loadArea(e.target.value);
});

// Phone: one panel open at a time (native exclusive <details>), legend starts folded,
// and Leaflet's buttons sit below the floating cards.
if (PHONE.matches) {
  $('legend-card').open = false;
  $('info-card').name = $('legend-card').name = 'panels';
}
new ResizeObserver(([entry]) => {
  document.documentElement.style.setProperty('--top-ui-h', entry.target.offsetHeight + 'px');
}).observe($('top-ui'));

// ---------- start ----------
updateLegend(currentLayer);
loadCities();
