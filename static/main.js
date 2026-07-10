// ── State ────────────────────────────────────────────────────────────────────
let nodesData      = [];
let routePolylines = {};
let markers        = {};
let busMarkers     = {};
let isPlaying      = false;
let playInterval   = null;
let currentSelectedStop = null;
let stateHistory   = [];
let playbackSpeed  = 800; // Default to Slow for better readability
let currentAlgo    = 'Greedy';
let totalReallocations = 0;
let logCount       = 0;
let prevBusRoutes  = {};
let notifTimer     = null;

// ── Map ──────────────────────────────────────────────────────────────────────
const map = L.map('map', { zoomControl: false }).setView([22.72, 75.88], 12);
L.control.zoom({ position: 'topright' }).addTo(map);

L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap © CARTO'
}).addTo(map);

// Labels layer on top so text is readable
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
    pane:    'overlayPane',
    zIndex:  400
}).addTo(map);

const ROUTE_COLORS = {
    R08: '#7a5090', R09: '#1a8070', R13: '#e67e22',
    R15: '#3b78b5', R16: '#c0392b', R18: '#27ae60'
};
function routeColor(id) { return ROUTE_COLORS[id] || '#3e4857'; }

// ── Chart ────────────────────────────────────────────────────────────────────
// Pre-fill labels from 06:00 to 09:10 (191 minutes)
const chartLabels = [];
for (let i = 0; i <= 190; i++) {
    const totalMins = 360 + i;
    const h = Math.floor(totalMins / 60);
    const m = totalMins % 60;
    chartLabels.push(`${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`);
}

const ctx = document.getElementById('chart').getContext('2d');
const strandedChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: chartLabels,
        datasets: [{
            data: new Array(191).fill(null),
            borderColor: '#c94040',
            backgroundColor: 'rgba(201,64,64,0.08)',
            borderWidth: 1.5,
            pointRadius: 0,
            fill: true,
            tension: 0.3,
            spanGaps: true
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        scales: {
            x: { 
                display: true, 
                grid: { display: false },
                ticks: { color: '#3e4857', font: { family: "'IBM Plex Mono'", size: 9 }, maxTicksLimit: 6 }
            },
            y: {
                beginAtZero: true,
                grid: { color: 'rgba(255,255,255,0.04)', drawBorder: false },
                ticks: { color: '#3e4857', font: { family: "'IBM Plex Mono'", size: 9 }, maxTicksLimit: 4 }
            }
        },
        plugins: { legend: { display: false } }
    }
});

// ── Bus markers ───────────────────────────────────────────────────────────────
const getBusSvg = (color, isHelper) => {
    const stroke = isHelper ? '#f0c060' : 'rgba(255,255,255,0.7)';
    const strokeWidth = isHelper ? '2' : '1';
    // Professional bus SVG path
    return `<svg width="22" height="22" viewBox="0 0 24 24" fill="${color}" stroke="${stroke}" stroke-width="${strokeWidth}" stroke-linecap="round" stroke-linejoin="round" style="${isHelper ? 'filter: drop-shadow(0 0 4px #d4922a);' : 'filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5));'}"><path d="M4 16c0 .88.39 1.67 1 2.22V20c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h8v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1.78c.61-.55 1-1.34 1-2.22V6c0-3.5-3.58-4-8-4s-8 .5-8 4v10zm3.5 1c-.83 0-1.5-.67-1.5-1.5S6.67 14 7.5 14s1.5.67 1.5 1.5S8.33 17 7.5 17zm9 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm1.5-6H6V6h12v5z"/></svg>`;
};

const ICON_NORMAL = (routeId) => {
    const c = routeColor(routeId);
    return L.divIcon({
        html: getBusSvg(c, false),
        className: '',
        iconSize: [22, 22],
        iconAnchor: [11, 11]
    });
};

const ICON_HELPER = () => L.divIcon({
    html: getBusSvg('#d4922a', true),
    className: '',
    iconSize: [24, 24],
    iconAnchor: [12, 12]
});

const ICON_ACRO = () => L.divIcon({
    html: `<div style="
        width:10px; height:10px;
        background:#c94040;
        border:1.5px solid #e07070;
        border-radius:50%;
    "></div>`,
    className: '',
    iconSize: [10, 10],
    iconAnchor: [5, 5]
});

// ── Algo selector ─────────────────────────────────────────────────────────────
function selectAlgo(algo) {
    currentAlgo = algo;
    document.querySelectorAll('.algo-row').forEach(el => el.classList.remove('active'));
    const id = 'algo-' + algo.toLowerCase();
    if (document.getElementById(id)) document.getElementById(id).classList.add('active');
}

// ── Topology ─────────────────────────────────────────────────────────────────
async function fetchTopology() {
    const res  = await fetch('/topology');
    const data = await res.json();

    nodesData = data.nodes.map(n => ({
        id:      n.id,
        name:    n.name,
        lat:     n.y,
        lng:     n.x,
        routeId: n.route_id || n.id.split('-')[0]
    }));

    drawMap(data.edges);
}

function drawMap(edges) {
    Object.values(routePolylines).forEach(pl => { if (map.hasLayer(pl)) map.removeLayer(pl); });
    Object.values(markers).forEach(m => { if (map.hasLayer(m)) map.removeLayer(m); });
    routePolylines = {};
    markers = {};

    // Route polylines
    edges.forEach(e => {
        const src = nodesData.find(n => n.id === e.source);
        const tgt = nodesData.find(n => n.id === e.target);
        if (!src || !tgt) return;
        const rid = src.id === 'ACROPOLIS' ? tgt.routeId : src.routeId;
        const pl = L.polyline([[src.lat, src.lng], [tgt.lat, tgt.lng]], {
            color:   routeColor(rid),
            weight:  2.5,
            opacity: 0.6,
        }).addTo(map);
        routePolylines[`${e.source}|${e.target}`] = pl;
    });

    // Stop circles
    nodesData.forEach(n => {
        const isAcro = n.id === 'ACROPOLIS';
        let m;
        if (isAcro) {
            m = L.circleMarker([n.lat, n.lng], {
                radius: 7, fillColor: '#c94040', color: '#e07070',
                weight: 1.5, fillOpacity: 1, opacity: 1
            }).addTo(map);
        } else {
            m = L.circleMarker([n.lat, n.lng], {
                radius: 3.5,
                fillColor: routeColor(n.routeId),
                color: 'rgba(255,255,255,0.2)',
                weight: 1,
                fillOpacity: 0.7
            }).addTo(map);
        }
        m.bindTooltip(
            `<span style="font-family:'IBM Plex Mono',monospace;font-size:11px;">${n.name}</span>`,
            { direction: 'top', className: 'dispatch-tip' }
        );
        m.on('click', () => {
            currentSelectedStop = n.id;
            document.getElementById('selected-node-name').innerText = n.name;
            document.getElementById('inject-panel').style.display = 'block';
        });
        markers[n.id] = m;
    });
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmtTime(mins) {
    const h = Math.floor(mins / 60), m = mins % 60;
    return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`;
}

function showNotif(text) {
    const bar = document.getElementById('notif-bar');
    document.getElementById('notif-text').innerText = text;
    bar.classList.add('visible');
    clearTimeout(notifTimer);
    notifTimer = setTimeout(() => bar.classList.remove('visible'), 8000); // 8 seconds instead of 3.5
}

function pulseAt(lat, lng) {
    const pt = map.latLngToContainerPoint([lat, lng]);
    const r  = document.createElement('div');
    r.className = 'evt-ring';
    r.style.cssText = `left:${pt.x-14}px;top:${pt.y-14}px;width:28px;height:28px;`;
    document.getElementById('map').appendChild(r);
    setTimeout(() => r.remove(), 1100);
}

function addLog(text, type) {
    const box = document.getElementById('action-log');
    const atBottom = box.scrollHeight - box.clientHeight <= box.scrollTop + 16;

    const div = document.createElement('div');
    div.className = 'log-entry' + (
        type === 'reassign' ? ' log-reassign' :
        type === 'arrive'   ? ' log-arrive'   :
        type === 'end'      ? ' log-end'      : ''
    );
    div.textContent = text;
    box.appendChild(div);

    if (atBottom) box.scrollTop = box.scrollHeight;

    logCount++;
    document.getElementById('log-count').textContent = `${logCount} entries`;
}

// ── Render ────────────────────────────────────────────────────────────────────
function renderState(state) {
    document.getElementById('time-display').textContent = fmtTime(state.time_mins);
    document.getElementById('val-stranded').textContent = state.stranded;
    document.getElementById('val-moved').textContent    = state.transported;
    document.getElementById('val-buses').textContent    = state.buses.length;

    // Stop demand colours
    state.nodes.forEach(ns => {
        const m = markers[ns.id];
        if (!m || ns.id === 'ACROPOLIS') return;
        const w = ns.waiting;
        const r = 3.5 + Math.min(w / 3.5, 14);
        m.setRadius(r);
        const col = w > 30 ? '#c94040' : w > 10 ? '#d4922a' : w > 0 ? '#3a9e6a' : routeColor(ns.id.split('-')[0]);
        m.setStyle({ fillColor: col, color: 'rgba(255,255,255,0.15)' });
    });

    // Bus positions
    Object.values(busMarkers).forEach(b => { if (map.hasLayer(b)) map.removeLayer(b); });
    busMarkers = {};

    state.buses.forEach(b => {
        const pNode = nodesData.find(n => n.id === b.prev_stop);
        const tNode = nodesData.find(n => n.id === b.target_stop);
        if (!pNode || !tNode) return;

        const lat = pNode.lat + (tNode.lat - pNode.lat) * b.progress;
        const lng = pNode.lng + (tNode.lng - pNode.lng) * b.progress;

        // Detect reassignment
        const prev = prevBusRoutes[b.id];
        if (prev && prev !== b.route && b.is_helper) {
            totalReallocations++;
            document.getElementById('val-realloc').textContent = totalReallocations;
            showNotif(`Scheduler: Bus ${b.id} diverted ${prev} → ${b.route}`);
            pulseAt(lat, lng);
        }
        prevBusRoutes[b.id] = b.route;

        const icon = b.is_helper ? ICON_HELPER() : ICON_NORMAL(b.route);
        const bm = L.marker([lat, lng], {
            icon,
            zIndexOffset: b.is_helper ? 800 : 400
        }).addTo(map);

        const arrText = b.target_stop === 'ACROPOLIS' && b.progress > 0.5
            ? ' [arriving]' : '';

        bm.bindTooltip(
            `<span style="font-family:'IBM Plex Mono',monospace;font-size:11px;line-height:1.5;">` +
            `Bus ${b.id}  ${b.route}${b.is_helper ? ' [diverted]' : ''}${arrText}<br>` +
            `${b.occ}/${b.cap} seats  ${b.state || ''}` +
            `</span>`,
            { direction: 'top', className: 'dispatch-tip' }
        );
        busMarkers[b.id] = bm;
    });
}

// ── Step ──────────────────────────────────────────────────────────────────────
async function stepSim() {
    let state;
    const slider = document.getElementById('timeline-scrub');
    const idx = parseInt(slider.value);

    if (idx < stateHistory.length - 1) {
        slider.value = idx + 1;
        state = stateHistory[idx + 1];
    } else {
        const res = await fetch('/step', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ steps: 1 })
        });
        state = await res.json();
        stateHistory.push(state);
        slider.max   = stateHistory.length - 1;
        slider.value = stateHistory.length - 1;

        strandedChart.data.datasets[0].data[idx + 1] = state.stranded;
        strandedChart.update();

        state.logs.forEach(l => {
            const isSched  = l.includes('SCHEDULER') || l.includes('DP_SCHEDULER') || l.includes('Reassigned');
            const isArrive = l.includes('ARRIVE') || l.includes('Acropolis') || l.includes('arrived');
            const clean    = l.replace(/^\[BOARD\]\s*/, '');
            addLog(clean, isSched ? 'reassign' : isArrive ? 'arrive' : 'normal');
        });

        if (state.done) {
            clearInterval(playInterval);
            playInterval = null;
            isPlaying = false;
            document.getElementById('play-btn').style.display  = 'inline-block';
            document.getElementById('pause-btn').style.display = 'none';
            document.querySelector('.status-text').textContent = 'ENDED';
            addLog(
                `SHIFT ENDED  ${fmtTime(state.time_mins)}  |  stranded: ${state.stranded}  transported: ${state.transported}`,
                'end'
            );
        }
    }

    renderState(state);
}

// ── Timeline ─────────────────────────────────────────────────────────────────
function scrubTimeline(val) {
    const idx = parseInt(val);
    if (idx >= 0 && idx < stateHistory.length) renderState(stateHistory[idx]);
}

// ── Reset ─────────────────────────────────────────────────────────────────────
async function resetSim() {
    clearInterval(playInterval);
    playInterval = null;
    isPlaying = false;
    document.getElementById('play-btn').style.display  = 'inline-block';
    document.getElementById('pause-btn').style.display = 'none';

    await fetch('/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scheduler: currentAlgo })
    });

    stateHistory = [];
    totalReallocations = 0;
    logCount = 0;
    prevBusRoutes = {};

    const slider = document.getElementById('timeline-scrub');
    slider.max = 0; slider.value = 0;

    strandedChart.data.datasets[0].data = new Array(191).fill(null);
    strandedChart.update();

    document.getElementById('action-log').innerHTML = '';
    document.getElementById('log-count').textContent = '0 entries';
    document.getElementById('time-display').textContent = '06:00';
    document.getElementById('val-stranded').textContent = '0';
    document.getElementById('val-moved').textContent    = '0';
    document.getElementById('val-realloc').textContent  = '0';
    document.getElementById('val-buses').textContent    = '—';
    document.querySelector('.status-text').textContent  = 'RUNNING';

    Object.values(busMarkers).forEach(b => { if (map.hasLayer(b)) map.removeLayer(b); });
    busMarkers = {};

    await fetchTopology();
    addLog(`[RESET] ${currentAlgo} scheduler loaded. Simulation ready.`, 'arrive');
}

// ── Play / Pause ──────────────────────────────────────────────────────────────
function togglePlay() {
    isPlaying = !isPlaying;
    document.getElementById('play-btn').style.display  = isPlaying ? 'none' : 'inline-block';
    document.getElementById('pause-btn').style.display = isPlaying ? 'inline-block' : 'none';
    if (isPlaying) {
        playInterval = setInterval(stepSim, playbackSpeed);
    } else {
        clearInterval(playInterval);
        playInterval = null;
    }
}

function updateSpeed() {
    playbackSpeed = parseInt(document.getElementById('speed-select').value);
    if (isPlaying) {
        clearInterval(playInterval);
        playInterval = setInterval(stepSim, playbackSpeed);
    }
}

// ── Inject ────────────────────────────────────────────────────────────────────
async function injectPassengers() {
    if (!currentSelectedStop) return;
    const slider = document.getElementById('timeline-scrub');
    if (parseInt(slider.value) < stateHistory.length - 1) {
        alert('Scrub to current tick before injecting demand.');
        return;
    }
    const students = parseInt(document.getElementById('inject-students').value) || 0;
    const faculty  = parseInt(document.getElementById('inject-faculty').value)  || 0;

    await fetch('/inject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stop_id: currentSelectedStop, students, faculty })
    });

    const name = document.getElementById('selected-node-name').textContent;
    addLog(`[INJECT] ${name}  students:${students}  faculty:${faculty}`, 'arrive');

    const m = markers[currentSelectedStop];
    if (m) {
        m.setStyle({ fillColor: '#d4922a' });
        setTimeout(() => m.setStyle({ fillColor: '#c94040' }), 600);
    }
}

// ── Boot ──────────────────────────────────────────────────────────────────────
window.onload = resetSim;
