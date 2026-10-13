/*
 * Petrolmate card — cheapest / closest fuel at your fuel brands, after your discounts, with filters and a map.
 * Served and registered by the Petrolmate integration; no separate resource needed.
 *
 *   type: custom:petrolmate-card
 *   # all optional:
 *   title: Fuel
 *   entity: select.petrolmate_fuel_type   # pick an entry when you have several
 *   count: 3                             # stations per column (1–10)
 *   columns: both                        # both | cheapest | closest
 *   map: true
 *   map_height: 340
 *   maps: auto                           # directions app: auto (Apple on iPhone/iPad/Mac, Google elsewhere) | apple | google
 *   logos: { bp: /local/logos/bp.svg }    # override a network's logo (defaults come from the integration)
 */
const PM_VERSION = '1.1.6';

const LETTERS = 'ABCDEFGHIJ';
// discount colours, in pill order; tiles show a matching dot
const DISC_COLOURS = ['#14b8a6', '#a855f7', '#ec4899', '#3b82f6', '#f97316', '#84cc16'];
const DEFAULTS = {
  title: 'Fuel', entity: '', count: 3, columns: 'both', maps: 'auto', map: true, map_height: 340,
  show_brands: true, show_any: true, show_other: true, show_fuels: true, show_discounts: true, other_line: true, times: true, logos: true,
};

const FUEL_SHORT = { DIESEL: 'Diesel', ULP: 'ULP', E10: 'E10', PULP95: '95', PULP98: '98', LPG: 'LPG' };

const LIBS = {
  leafletCss: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css',
  leaflet: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js',
  maplibreCss: 'https://cdnjs.cloudflare.com/ajax/libs/maplibre-gl/4.7.1/maplibre-gl.css',
  maplibre: 'https://cdnjs.cloudflare.com/ajax/libs/maplibre-gl/4.7.1/maplibre-gl.js',
  bridge: 'https://unpkg.com/@maplibre/maplibre-gl-leaflet@0.1.3/leaflet-maplibre-gl.js',
};
const _scripts = {};
function loadScript(src) {
  return _scripts[src] ||= new Promise((ok, fail) => {
    const s = document.createElement('script');
    s.src = src; s.onload = ok; s.onerror = () => fail(new Error('load failed: ' + src));
    document.head.appendChild(s);
  });
}
async function loadMapLibs() {
  if (!window.L) await loadScript(LIBS.leaflet);
  if (!window.maplibregl) await loadScript(LIBS.maplibre);
  if (!window.L.maplibreGL) await loadScript(LIBS.bridge);
}

// Apple Maps on Apple devices (incl. iPadOS, which reports itself as a Mac), Google Maps everywhere else
const IS_APPLE = /iPhone|iPad|iPod|Macintosh/.test(navigator.userAgent);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const money = (c) => '$' + (c / 100).toFixed(3); // c/L → $/L
// feed timestamps are UTC without a zone; show when the price was set
function since(u) {
  if (!u) return '';
  const d = new Date(/Z|[+-]\d\d:?\d\d$/.test(u) ? u : u + 'Z'), now = new Date(), h = (now - d) / 3.6e6;
  if (d.toDateString() === now.toDateString()) return 'since ' + d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }).replace(' ', '');
  if (h < 6 * 24) return 'since ' + d.toLocaleDateString(undefined, { weekday: 'short' });
  return 'since ' + d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
}

const STYLE = `
:host{display:block}
ha-card{padding:12px 12px 10px;overflow:hidden}
.hdr{display:flex;align-items:center;gap:8px;margin:2px 4px 8px}
.hdr .t{flex:1;font-size:18px;font-weight:600}
.hdr ha-icon{--mdc-icon-size:20px;color:var(--secondary-text-color);cursor:pointer}
.chips{display:flex;flex-wrap:wrap;justify-content:center;gap:6px;margin:0 0 8px}
.chip{display:inline-flex;align-items:center;gap:4px;height:30px;padding:0 10px 0 6px;border-radius:15px;cursor:pointer;user-select:none;
  font-size:13px;font-weight:600;background:var(--secondary-background-color);color:var(--primary-text-color);border:1px solid var(--divider-color)}
.chip ha-icon{--mdc-icon-size:18px;color:var(--disabled-text-color, #9e9e9e)}
.chip.on ha-icon{color:var(--cc)}
.chip.dim{opacity:.45}
.dots{display:inline-flex;gap:2px;margin-left:4px;vertical-align:2px}
.dots i{width:8px;height:8px;border-radius:50%;background:var(--dc)}
.cols.one{grid-template-columns:1fr}
.cap{margin:2px 4px 4px;text-align:center;font-size:10.5px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--secondary-text-color)}
.off{font-size:.8em;font-weight:600;color:var(--success-color,#43a047)}
.tile .h s{font-size:.7em;font-weight:400;color:var(--secondary-text-color);margin-left:3px}
.co-price s{font-size:.8em;font-weight:400;color:var(--secondary-text-color)}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:4px}
.colh{display:flex;align-items:center;gap:6px;font-size:15px;font-weight:600;margin:4px 4px 0}
.colh ha-icon{--mdc-icon-size:18px}
.tile{position:relative;overflow:hidden;cursor:pointer;min-height:64px;padding:8px 10px 8px 12px;border-radius:12px;
  background:var(--secondary-background-color);border:1px solid var(--divider-color)}
/* logo wash: whole logo fitted in a box on the right, fading out to the left */
.tile::before{content:'';position:absolute;top:10px;bottom:10px;right:10px;width:min(30%,84px);pointer-events:none;
  background:var(--logo,none) right center/contain no-repeat;opacity:.35;
  -webkit-mask-image:linear-gradient(to right,transparent,#000 70%);mask-image:linear-gradient(to right,transparent,#000 70%)}
.tile>*{position:relative}
.tile.empty{visibility:hidden}
.tile .h{font-size:15px}
.tile .h .g{white-space:nowrap}
/* cheapest, or tied with it: the same double ring as its map bubble */
.tile.best{box-shadow:0 0 0 2px var(--card-background-color),0 0 0 4px var(--c)}
.tile .st{font-size:12.5px;font-weight:600;line-height:1.25;margin-top:2px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.tile .dt{font-size:11px;color:var(--secondary-text-color);margin-top:2px}
.bd{display:inline-flex;align-items:center;justify-content:center;min-width:18px;height:18px;padding:0 3px;box-sizing:border-box;border-radius:9px;
  background:var(--c);color:#fff;font-size:11px;font-weight:700;margin-right:6px;vertical-align:1px}
.any{margin-top:8px;padding:8px 12px;border-radius:12px;font-size:12.5px;cursor:pointer;background:var(--secondary-background-color);border:1px dashed var(--divider-color)}
.none{padding:16px;text-align:center;color:var(--secondary-text-color)}
.mapwrap{position:relative;margin-top:10px;border-radius:12px;overflow:hidden;background:var(--secondary-background-color)}
.map{position:absolute;inset:0}
.fit{position:absolute;right:10px;bottom:24px;z-index:500;width:34px;height:34px;border-radius:10px;display:flex;align-items:center;justify-content:center;cursor:pointer;
  background:var(--card-background-color);border:1px solid var(--divider-color);color:var(--primary-text-color)}
.fit ha-icon{--mdc-icon-size:18px}
/* compact attribution: an (i) that reveals the OpenStreetMap credit, like HA's own map */
.info{position:absolute;left:8px;bottom:8px;z-index:600;width:20px;height:20px;border-radius:50%;display:flex;align-items:center;justify-content:center;cursor:pointer;
  font:700 12px/1 Georgia,serif;font-style:italic;background:var(--card-background-color);color:var(--primary-text-color);border:1px solid var(--divider-color)}
.mapwrap .leaflet-control-attribution{display:none;margin:0 0 8px 34px!important;border-radius:10px;padding:2px 8px;font-size:11px;
  background:var(--card-background-color)!important;color:var(--secondary-text-color)}
.mapwrap.attr .leaflet-control-attribution{display:block}
.leaflet-control-attribution a{color:var(--primary-color)}
.foot{margin:8px 4px 0;font-size:11px;color:var(--secondary-text-color)}
/* map markers: dot on the exact spot + callout bubble */
.mk{position:relative;width:0;height:0}
.mk .dot{position:absolute;left:-6px;top:-6px;width:8px;height:8px;border-radius:50%;background:var(--c);border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.5)}
.bub{position:absolute;display:flex;align-items:center;gap:5px;height:24px;padding:0 8px 0 3px;border-radius:12px;white-space:nowrap;cursor:pointer;
  background:var(--card-background-color);color:var(--primary-text-color);border:2px solid var(--c);box-shadow:0 2px 6px rgba(0,0,0,.4);font:700 13px/1 var(--primary-font-family, sans-serif)}
.bub .lb{min-width:18px;height:18px;padding:0 3px;box-sizing:border-box;border-radius:9px;background:var(--c);color:#fff;font-size:11px;display:flex;align-items:center;justify-content:center}
.bub::after{content:"";position:absolute;border:6px solid transparent}
.bub.up{left:0;bottom:10px;transform:translateX(-50%)} .bub.up::after{top:100%;left:50%;margin-left:-6px;border-top-color:var(--c)}
.bub.down{left:0;top:10px;transform:translateX(-50%)} .bub.down::after{bottom:100%;left:50%;margin-left:-6px;border-bottom-color:var(--c)}
.bub.right{left:10px;top:0;transform:translateY(-50%)} .bub.right::after{right:100%;top:50%;margin-top:-6px;border-right-color:var(--c)}
.bub.left{right:10px;top:0;transform:translateY(-50%)} .bub.left::after{left:100%;top:50%;margin-top:-6px;border-left-color:var(--c)}
.mk.best .bub{box-shadow:0 0 0 2px var(--card-background-color),0 0 0 4px var(--c),0 2px 8px rgba(0,0,0,.5)}
.me{width:16px;height:16px;border-radius:50%;background:#2a8cff;border:3px solid #fff;animation:pm-pulse 2s infinite}
@keyframes pm-pulse{0%{box-shadow:0 0 0 0 rgba(42,140,255,.55)}70%{box-shadow:0 0 0 14px rgba(42,140,255,0)}100%{box-shadow:0 0 0 0 rgba(42,140,255,0)}}
.leaflet-container{font-family:var(--primary-font-family, sans-serif);background:var(--secondary-background-color)}
.leaflet-popup-content-wrapper,.leaflet-popup-tip{background:var(--card-background-color);color:var(--primary-text-color)}
.leaflet-popup-content{margin:12px 14px;min-width:180px}
.co-name{font-weight:700;font-size:14px}
.co-addr,.co-meta{font-size:12px;color:var(--secondary-text-color);margin:2px 0}
.co-price{font-size:22px;font-weight:800;margin-top:6px}
.co-price small{font-size:12px;font-weight:600;color:var(--secondary-text-color)}
.co-go{margin-top:10px;text-align:center;padding:9px 0;border-radius:10px;font-weight:700;font-size:14px;color:#fff;background:var(--primary-color, #2a8cff);cursor:pointer}
`;

// The class is created lazily: HA swaps in a scoped custom-element registry (and HTMLElement) while its app
// bundle starts, and this module can run before that. Defining early lands in a registry HA no longer reads.
const makeCard = () => class PetrolmateCard extends HTMLElement {
  setConfig(config) {
    this._config = { ...DEFAULTS, ...config };
    this._logos = config.logos || {}; // per-network overrides; defaults come from the integration
    this._built = false;
    this._key = null; this._mkey = null;
  }

  static getStubConfig() { return {}; }
  static getConfigElement() { return document.createElement('petrolmate-card-editor'); }
  getCardSize() { return 12; }
  getGridOptions() { return { columns: 'full' }; }

  set hass(hass) {
    this._hass = hass;
    if (!this._built) this._build();
    const ents = this._entities();
    const loc = ents && ents.stations && hass.states[ents.stations] && hass.states[ents.stations].attributes.location_entity;
    const key = JSON.stringify(ents && [
      [...ents.all, loc].map((e) => hass.states[e] && [hass.states[e].state, hass.states[e].last_updated]),
      hass.themes && hass.themes.darkMode,
    ]);
    if (key === this._key) return;
    this._key = key;
    this._render(ents);
  }

  // ---- entity discovery: everything on the same device as the fuel-type select ----
  _entities() {
    const hass = this._hass, reg = hass.entities || {};
    let select = this._config.entity;
    if (!select) select = Object.keys(hass.states).find((e) => e.startsWith('select.') && reg[e] && reg[e].platform === 'petrolmate');
    if (!select || !hass.states[select]) return null;
    const dev = reg[select] && reg[select].device_id;
    const mine = Object.keys(reg).filter((e) => reg[e].platform === 'petrolmate' && (!dev || reg[e].device_id === dev) && hass.states[e]);
    const fuels = {}, switches = [], discounts = [];
    let stations = null, refresh = null, any = null, other = null;
    for (const e of mine) {
      const a = hass.states[e].attributes;
      if (e.startsWith('sensor.') && a.fuel) fuels[a.fuel] = e;
      else if (e.startsWith('sensor.') && 'location_entity' in a) stations = e;
      else if (e.startsWith('switch.') && a.network) switches.push(e);
      else if (e.startsWith('switch.') && a.any_brand) any = e;
      else if (e.startsWith('switch.') && a.other_brands) other = e;
      else if (e.startsWith('switch.') && a.discount) discounts.push(e);
      else if (e.startsWith('button.')) refresh = e;
    }
    const order = Object.keys(FUEL_SHORT);
    switches.sort((a, b) => hass.states[a].attributes.network.localeCompare(hass.states[b].attributes.network));
    discounts.sort((a, b) => String(hass.states[a].attributes.label).localeCompare(hass.states[b].attributes.label));
    return { select, fuels, fuelOrder: order.filter((f) => fuels[f]), switches, any, other, discounts, stations, refresh, all: [select, ...mine] };
  }

  _build() {
    this._built = true;
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
    const h = this._config.map_height;
    this.shadowRoot.innerHTML = `
      <link rel="stylesheet" href="${LIBS.leafletCss}"><link rel="stylesheet" href="${LIBS.maplibreCss}">
      <style>${STYLE}</style>
      <ha-card>
        <div class="dyn"></div>
        ${this._config.map ? `<div class="mapwrap" style="height:${h}px"><div class="map"></div><div class="info" title="Map data">i</div><div class="fit" title="Show all"><ha-icon icon="mdi:fit-to-screen-outline"></ha-icon></div></div>` : ''}
        <div class="foot"></div>
      </ha-card>`;
    const root = this.shadowRoot;
    root.querySelector('.dyn').addEventListener('click', (ev) => this._click(ev));
    const info = root.querySelector('.info');
    if (info) info.addEventListener('click', () => root.querySelector('.mapwrap').classList.toggle('attr'));
    const fit = root.querySelector('.fit');
    if (fit) fit.addEventListener('click', () => { this._userMoved = false; this._map && this._map.closePopup(); this._fit(); });
    this._map = null; this._markers = [];
  }

  _click(ev) {
    const el = ev.target.closest('[data-act]');
    if (!el) return;
    const { act, ent, val } = el.dataset, hass = this._hass;
    if (act === 'toggle') hass.callService('switch', 'toggle', { entity_id: ent });
    else if (act === 'fuel') hass.callService('select', 'select_option', { entity_id: ent, option: val });
    else if (act === 'refresh') hass.callService('button', 'press', { entity_id: ent });
    else if (act === 'go') window.open(val, '_blank');
  }

  _render(ents) {
    const root = this.shadowRoot, dyn = root.querySelector('.dyn'), hass = this._hass;
    if (!ents) {
      dyn.innerHTML = `<div class="none">Petrolmate: no entities found. Add the integration, or set <code>entity:</code> to its fuel-type select.</div>`;
      return;
    }
    const sel = hass.states[ents.select], fuel = sel.attributes.fuel;
    const sensor = hass.states[ents.fuels[fuel]];
    const a = (sensor && sensor.attributes) || {};
    const colors = a.network_colors || {};
    const colour = (r) => colors[r.network] || '#888';
    const netLogos = Object.fromEntries(ents.switches.map((e) => [hass.states[e].attributes.network, hass.states[e].attributes.logo]));
    const logo = (r) => this._logos[r.network] || netLogos[r.network];
    this._colour = colour;

    const anyOn = !!(ents.any && hass.states[ents.any].state === 'on');
    const chip = (e, label, colour, dim) => {
      const on = hass.states[e].state === 'on';
      return `<div class="chip ${on ? 'on' : ''} ${dim ? 'dim' : ''}" style="--cc:${colour}" data-act="toggle" data-ent="${e}">
        <ha-icon icon="${on ? 'mdi:checkbox-marked-circle' : 'mdi:checkbox-blank-circle-outline'}"></ha-icon>${esc(label)}</div>`;
    };
    const netChips = (ents.any && this._config.show_any ? chip(ents.any, 'Any', 'var(--primary-color)') : '')
      + ents.switches.map((e) => chip(e, hass.states[e].attributes.label, hass.states[e].attributes.color, anyOn)).join('')
      + (ents.other && this._config.show_other ? chip(ents.other, 'Other', '#888', anyOn) : '');
    const discColour = {};
    const discChips = ents.discounts.map((e, i) => {
      const at = hass.states[e].attributes;
      discColour[at.label] = DISC_COLOURS[i % DISC_COLOURS.length];
      return chip(e, `${at.label} −${at.cents}c`, discColour[at.label]);
    }).join('');
    this._discColour = discColour;
    const codes = sel.attributes.codes || {};
    const fuelChips = ents.fuelOrder.map((f) => {
      const opt = Object.keys(codes).find((k) => codes[k] === f), on = f === fuel;
      return `<div class="chip ${on ? 'on' : ''}" style="--cc:var(--primary-color)" data-act="fuel" data-ent="${ents.select}" data-val="${esc(opt)}">
        <ha-icon icon="${on ? 'mdi:radiobox-marked' : 'mdi:radiobox-blank'}"></ha-icon>${FUEL_SHORT[f]}</div>`;
    }).join('');

    const cfg = this._config, count = Math.max(1, Math.min(10, +cfg.count || 3));
    const showC = cfg.columns !== 'closest', showN = cfg.columns !== 'cheapest';
    const allTop = a.top || [], best = allTop[0];
    const top = showC ? allTop.slice(0, count) : [], near = showN ? (a.closest || []).slice(0, count) : [];
    // a dot per discount applied, coloured like its pill
    const dots = (r) => (r.discount > 0
      ? `<span class="dots" title="${esc((r.discounts || []).join(' + '))}">${(r.discounts || []).map((n) => `<i style="--dc:${discColour[n] || '#888'}"></i>`).join('')}</span>` : '');
    this._best = best ? best.price : null;
    const isBest = (r) => this._best != null && r.price <= this._best + 0.05;
    const strike = (r) => (r.discount > 0 ? `<s>${money(r.pump_price)}</s>` : '');
    const vs = (r) => { const d = best ? r.price - best.price : 0; return d > 0.05 ? `+${+d.toFixed(1)}c vs cheapest` : 'cheapest'; };
    const detail = (...parts) => parts.filter(Boolean).join(' · ');
    // head = [first, second]: each group stays on one line; the second wraps below when the tile is narrow
    const tile = (r, lab, head, dt) => r
      ? `<div class="tile ${isBest(r) ? 'best' : ''}" style="--c:${colour(r)};${cfg.logos && logo(r) ? `--logo:url('${logo(r)}')` : ''}" data-act="go" data-val="${esc(this._dirUrl(r))}">
          <div class="h"><span class="g"><span class="bd">${lab}</span>${head[0]}</span> <span class="g">${head[1]}</span></div><div class="st">${esc(r.station)}</div>${dt ? `<div class="dt">${dt}</div>` : ''}</div>`
      : `<div class="tile empty"></div>`;
    let tiles = '';
    for (let i = 0; i < count; i++) {
      const c = top[i], n = near[i];
      if (showC) tiles += tile(c, i + 1, c && [`<b>${money(c.price)}</b>${strike(c)}${dots(c)}`, `· ${c.km} km`],
        c && detail(i > 0 && vs(c) !== 'cheapest' && vs(c), cfg.times && since(c.updated)));
      if (showN) tiles += tile(n, LETTERS[i], n && [`<b>${n.km}km</b> ·`, `${money(n.price)}${strike(n)}${dots(n)}`],
        n && detail(vs(n), cfg.times && since(n.updated)));
    }
    const any = a.cheapest_any_brand;
    const anyLine = cfg.other_line && !anyOn && any && best && any.price < best.price
      ? `<div class="any" data-act="go" data-val="${esc(this._dirUrl(any))}">Cheapest at other brands: <b>${money(any.price)}</b> at ${esc(any.station)} · ${any.km} km · ${+(best.price - any.price).toFixed(1)}c cheaper</div>` : '';

    dyn.innerHTML = `
      <div class="hdr"><span class="t">${esc(this._config.title)}</span>${ents.refresh ? `<ha-icon icon="mdi:refresh" data-act="refresh" data-ent="${ents.refresh}" title="Refresh"></ha-icon>` : ''}</div>
      ${cfg.show_brands ? `<div class="cap">Fuel brands</div><div class="chips">${netChips}</div>` : ''}
      ${cfg.show_fuels ? `<div class="cap">Fuel</div><div class="chips">${fuelChips}</div>` : ''}
      ${cfg.show_discounts && discChips ? `<div class="cap">My discounts</div><div class="chips">${discChips}</div>` : ''}
      <div class="cols ${showC && showN ? '' : 'one'}">
        ${showC ? '<div class="colh"><ha-icon icon="mdi:currency-usd"></ha-icon>Cheapest</div>' : ''}
        ${showN ? '<div class="colh"><ha-icon icon="mdi:map-marker-distance"></ha-icon>Closest</div>' : ''}
        ${top.length || near.length ? tiles : ''}
      </div>
      ${top.length || near.length ? '' : `<div class="none">No ${esc(a.fuel_name || 'fuel')} at your fuel brands nearby</div>`}
      ${anyLine}`;

    const st = ents.stations && hass.states[ents.stations];
    root.querySelector('.foot').textContent = st
      ? `${a.fuel_name || ''} · searched ${st.state} stations within ${st.attributes.reach_km} km · tap a station for directions` : '';

    if (this._config.map) this._renderMap(top, near, st).catch((e) => console.warn('petrolmate-card map:', e));
  }

  // ---- map ----
  async _renderMap(top, near, st) {
    await loadMapLibs();
    const L = window.L, hass = this._hass;
    if (!this._map) {
      const el = this.shadowRoot.querySelector('.map');
      this._map = L.map(el, { zoomControl: false, attributionControl: false, zoomSnap: 0.25, zoomDelta: 0.5 });
      L.control.attribution({ prefix: false, position: 'bottomleft' }).addTo(this._map);
      this._layer = L.layerGroup().addTo(this._map);
      this._map.setView([hass.config.latitude, hass.config.longitude], 11);
      this._map.on('dragstart', () => (this._userMoved = true));
      setTimeout(() => (this._armed = true), 1500);
      this._map.on('zoomstart', () => { if (this._armed && !this._fitting) this._userMoved = true; });
      this._map.on('zoomend', () => this._declutter());
      new ResizeObserver(() => { this._map.invalidateSize(); if (!this._userMoved) this._fit(); }).observe(el);
    }
    const dark = !!(hass.themes && hass.themes.darkMode);
    if (this._dark !== dark) {
      this._dark = dark;
      const attribution = '© <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors';
      let opts;
      try {
        // Home Assistant's own map (2026.x+): its light/dark style, tiles + fonts proxied through /api/map_tiles
        await this._mapToken();
        opts = { style: await this._haStyle(dark), transformRequest: (url) => this._tileRequest(url), attribution };
      } catch (e) {
        // older HA: the same VersaTiles vector tiles, straight from the public server
        opts = { style: `https://tiles.versatiles.org/assets/styles/${dark ? 'colorful-dark' : 'colorful'}/style.json`, attribution: attribution + ' · VersaTiles' };
      }
      if (this._tiles) this._map.removeLayer(this._tiles);
      this._tiles = L.maplibreGL(opts).addTo(this._map);
    }

    // union of both lists; label "1"/"A"/"1A"
    const rows = [];
    const add = (list, k) => (list || []).forEach((r, i) => {
      let x = rows.find((y) => y.station === r.station);
      if (!x) rows.push((x = { ...r }));
      x[k] = i;
    });
    add(top, 'cheap'); add(near, 'near');
    const loc = st && hass.states[st.attributes.location_entity];
    const me = loc && loc.attributes.latitude != null ? [loc.attributes.latitude, loc.attributes.longitude] : null;
    const mkey = JSON.stringify([rows.map((r) => [r.station, r.price, r.cheap, r.near]), me]);
    if (mkey === this._mkey) return;
    this._mkey = mkey;

    this._layer.clearLayers();
    const pts = [];
    this._markers = rows.map((r) => {
      const m = L.marker([r.latitude, r.longitude], { icon: this._icon(r, 'up'), zIndexOffset: r.cheap != null ? 1000 - r.cheap * 10 : 500 })
        .bindPopup(() => this._callout(r), { autoPanPadding: [20, 60] }).addTo(this._layer);
      m.r = r; m.pos = 'up';
      pts.push([r.latitude, r.longitude]);
      return m;
    });
    if (me) {
      L.marker(me, { icon: L.divIcon({ className: '', html: '<div class="me"></div>', iconSize: [22, 22], iconAnchor: [11, 11] }), interactive: false }).addTo(this._layer);
      pts.push(me);
    }
    this._bounds = pts.length ? L.latLngBounds(pts) : null;
    if (!this._userMoved) this._fit();
    this._declutter();
  }

  // ---- HA map tiles: short-lived access token from the websocket, renewed every 15 min ----
  async _mapToken() {
    if (this._tok && Date.now() - this._tokAt < 15 * 60e3) return this._tok;
    const r = await this._hass.connection.sendMessagePromise({ type: 'map_tiles/access_token' });
    this._tok = r.token; this._tokAt = Date.now();
    if (!this._tokTimer) this._tokTimer = setInterval(() => this._mapToken().catch(() => {}), 15 * 60e3);
    return this._tok;
  }

  async _haStyle(dark) {
    const res = await fetch(`/static/map/${dark ? 'dark' : 'light'}.json`);
    if (!res.ok) throw new Error('no HA map style');
    const st = await res.json();
    const abs = (u) => (u.startsWith('/') ? location.origin + u : u); // string concat keeps {fontstack} braces intact
    for (const src of Object.values(st.sources || {})) if (src.url) src.url = abs(src.url);
    if (typeof st.glyphs === 'string') st.glyphs = abs(st.glyphs);
    if (typeof st.sprite === 'string') st.sprite = abs(st.sprite);
    else if (Array.isArray(st.sprite)) st.sprite = st.sprite.map((x) => ({ ...x, url: abs(x.url) }));
    return st;
  }

  _tileRequest(url) {
    let u;
    try { u = new URL(url, location.origin); } catch (e) { return { url }; }
    if (u.origin === location.origin && u.pathname.startsWith('/api/map_tiles/'))
      return { url: u.href, headers: { 'X-Map-Tiles-Token': this._tok } };
    return { url };
  }

  _dirUrl(r) {
    const app = this._config.maps === 'auto' ? (IS_APPLE ? 'apple' : 'google') : this._config.maps;
    const google = r.maps_google || `https://www.google.com/maps/dir/?api=1&destination=${r.latitude},${r.longitude}&travelmode=driving`;
    return app === 'google' ? google : r.maps;
  }

  _icon(r, pos) {
    const label = (r.cheap != null ? String(r.cheap + 1) : '') + (r.near != null ? LETTERS[r.near] : '');
    return window.L.divIcon({
      className: '', iconSize: [0, 0], iconAnchor: [0, 0], popupAnchor: [0, pos === 'down' ? 6 : -36],
      html: `<div class="mk ${this._best != null && r.price <= this._best + 0.05 ? 'best' : ''}" style="--c:${this._colour(r)}"><div class="dot"></div>
        <div class="bub ${pos}"><span class="lb">${label}</span>${money(r.price)}</div></div>`,
    });
  }

  _callout(r) {
    const div = document.createElement('div');
    const tags = [r.cheap != null ? 'Cheapest ' + (r.cheap + 1) : '', r.near != null ? 'Closest ' + LETTERS[r.near] : ''].filter(Boolean).join(' · ');
    div.innerHTML = `<div class="co-name">${esc(r.station)}</div><div class="co-addr">${esc(r.address)}</div><div class="co-meta">${tags}</div>
      <div class="co-price">${money(r.price)} <small>/L</small>${r.discount > 0 ? ` <s>${money(r.pump_price)}</s>` : ''}</div>
      ${r.discount > 0 ? `<div class="co-meta">−${r.discount}c ${esc((r.discounts || []).join(' + '))}</div>` : ''}<div class="co-meta">${r.km} km · ${since(r.updated)}</div><div class="co-go">Directions</div>`;
    div.querySelector('.co-go').addEventListener('click', () => window.open(this._dirUrl(r), '_blank'));
    return div;
  }

  // give each bubble the first side (up, down, right, left) that doesn't hit one already placed; cheapest first
  _declutter() {
    if (!this._map) return;
    const BW = 86, BH = 28, GAP = 10, placed = [];
    const rect = (p, k) => k === 'up' ? [p.x - BW / 2, p.y - GAP - BH, p.x + BW / 2, p.y - GAP]
      : k === 'down' ? [p.x - BW / 2, p.y + GAP, p.x + BW / 2, p.y + GAP + BH]
      : k === 'right' ? [p.x + GAP, p.y - BH / 2, p.x + GAP + BW, p.y + BH / 2]
      : [p.x - GAP - BW, p.y - BH / 2, p.x - GAP, p.y + BH / 2];
    const hit = (a, b) => a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3];
    this._markers.slice().sort((a, b) => (a.r.cheap ?? 9) - (b.r.cheap ?? 9)).forEach((m) => {
      const p = this._map.latLngToContainerPoint(m.getLatLng());
      const pos = ['up', 'down', 'right', 'left'].find((k) => !placed.some((q) => hit(rect(p, k), q))) || 'up';
      placed.push(rect(p, pos));
      if (m.pos !== pos) { m.pos = pos; m.setIcon(this._icon(m.r, pos)); }
    });
  }

  _fit() {
    if (!this._map || !this._bounds) return;
    this._fitting = true;
    if (this._bounds.getNorthEast().equals(this._bounds.getSouthWest())) this._map.setView(this._bounds.getCenter(), 14);
    else this._map.fitBounds(this._bounds, { padding: [50, 48], maxZoom: 16 });
    setTimeout(() => (this._fitting = false), 400);
  }
};

// ---- visual editor: HA's own form, filled with the defaults so toggles show their real state ----
const EDITOR_SCHEMA = [
  { name: 'title', selector: { text: {} } },
  { name: 'entity', selector: { entity: { filter: { integration: 'petrolmate', domain: 'select' } } } },
  { type: 'grid', name: '', schema: [
    { name: 'count', selector: { number: { min: 1, max: 10, mode: 'box' } } },
    { name: 'columns', selector: { select: { mode: 'dropdown', options: [
      { value: 'both', label: 'Cheapest and closest' }, { value: 'cheapest', label: 'Cheapest only' }, { value: 'closest', label: 'Closest only' }] } } },
  ] },
  { name: 'maps', selector: { select: { mode: 'dropdown', options: [
    { value: 'auto', label: 'Auto (Apple on iPhone/iPad/Mac, Google elsewhere)' }, { value: 'apple', label: 'Apple Maps' }, { value: 'google', label: 'Google Maps' }] } } },
  { type: 'grid', name: '', schema: [
    { name: 'map', selector: { boolean: {} } },
    { name: 'map_height', selector: { number: { min: 150, max: 900, step: 10, mode: 'box', unit_of_measurement: 'px' } } },
  ] },
  { type: 'expandable', name: '', title: 'Show on the card', flatten: true, schema: [
    { name: 'show_brands', selector: { boolean: {} } },
    { name: 'show_any', selector: { boolean: {} } },
    { name: 'show_other', selector: { boolean: {} } },
    { name: 'show_fuels', selector: { boolean: {} } },
    { name: 'show_discounts', selector: { boolean: {} } },
    { name: 'other_line', selector: { boolean: {} } },
    { name: 'times', selector: { boolean: {} } },
    { name: 'logos', selector: { boolean: {} } },
  ] },
];
const EDITOR_LABELS = {
  title: 'Title', entity: 'Petrolmate entry (fuel type select) — only needed with more than one',
  count: 'Stations per column', columns: 'Columns', maps: 'Directions app', map: 'Show map', map_height: 'Map height',
  show_brands: 'Fuel brand pills', show_any: '"Any" pill', show_other: '"Other" pill', show_fuels: 'Fuel pills', show_discounts: 'Discount pills',
  other_line: '"Cheapest at other brands" line', times: '"since…" times', logos: 'Brand logos',
};

const makeEditor = () => class PetrolmateCardEditor extends HTMLElement {
  setConfig(config) { this._config = config; this._render(); }
  set hass(hass) { this._hass = hass; this._render(); }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement('ha-form');
      this._form.schema = EDITOR_SCHEMA;
      this._form.computeLabel = (s) => EDITOR_LABELS[s.name] || s.title || s.name;
      this._form.addEventListener('value-changed', (ev) => this._changed(ev.detail.value));
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.data = { ...DEFAULTS, ...this._config };
  }

  // keep the YAML short: only write settings that differ from the defaults
  _changed(value) {
    const config = { type: this._config.type };
    for (const [k, v] of Object.entries(value)) {
      if (k === 'type' || v === undefined || v === '' || v === DEFAULTS[k]) continue;
      config[k] = v;
    }
    this._config = config;
    this.dispatchEvent(new CustomEvent('config-changed', { detail: { config }, bubbles: true, composed: true }));
  }
};

function registerCard() {
  if (customElements.get('petrolmate-card')) return;
  customElements.define('petrolmate-card-editor', makeEditor());
  customElements.define('petrolmate-card', makeCard());
  window.customCards = window.customCards || [];
  window.customCards.push({ type: 'petrolmate-card', name: 'Petrolmate', description: 'Cheapest and closest fuel at your card networks, with a map', preview: false });
  console.info(`%c PETROLMATE-CARD %c ${PM_VERSION} `, 'background:#009900;color:#fff', 'background:#333;color:#fff');
}
// wait (up to 10 s) for HA's registry polyfill, then register in the registry HA actually uses
(function whenReady(tries = 0) {
  if (window.CustomElementRegistryPolyfill || customElements.get('home-assistant') || tries > 200) registerCard();
  else setTimeout(() => whenReady(tries + 1), 50);
})();
