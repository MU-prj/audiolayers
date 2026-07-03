/* audiolayers gui — stato controlli -> API -> wav */
"use strict";

/* Definizione parametri: rispecchia bounds e default del motore.
   env: true = envelope-abile (editor breakpoint). */
const GLOBAL_DEFS = [
  { path: "sample_rate", label: "sample rate", kind: "select",
    options: [44100, 48000, 96000], def: 48000,
    info: "Frequenza di campionamento del progetto. Le sorgenti vengono ricampionate in ingresso (soxr VHQ)." },
  { path: "seed", label: "seed", kind: "int", def: 424242,
    info: "Riproducibilità: stesso seed → render identico bit per bit. Ogni layer e parametro ha il suo generatore derivato dal seed." },
  { path: "master_volume", label: "master (dB)", min: -60, max: 12, step: 0.5, def: 0, env: true,
    info: "Guadagno sul mix finale, in dB. Come curva diventa una dissolvenza globale per-campione." },
];
const LAYER_DEFS = [
  { path: "duration", label: "durata (s)", min: 1, max: 300, step: 1, def: 20,
    info: "Durata-obiettivo del layer. Non può essere una curva: è l'asse del tempo su cui corrono tutte le altre curve. L'ultimo grano non viene mai mozzato, quindi il layer può sforare di poco." },
  { path: "onset", label: "onset (s)", min: 0, max: 300, step: 0.5, def: 0,
    info: "Quando il layer entra sulla timeline globale, in secondi. Scalare per natura." },
  { path: "fill_factor", label: "fill factor", min: 0.05, max: 5, step: 0.05, def: 1, env: true,
    info: "Densità: intervallo tra i grani = durata grano ÷ fill factor. 1 = grani uno dietro l'altro; sotto 1 = silenzi; sopra 1 = sovrapposizioni (crossfade emergenti)." },
  { path: "fill_factor_range", label: "fill factor ±", min: 0, max: 2.5, step: 0.05, def: 0, env: true,
    info: "Variazione casuale del fill factor per grano: valore estratto uniformemente in [base−range, base+range] (tendency mask di Truax)." },
  { path: "distribution", label: "distribution", min: 0, max: 1, step: 0.01, def: 0, env: true,
    info: "Regolarità del tempo: 0 = metronomo, 1 = asincrono (intervalli casuali 0..2× l'intervallo sincrono), valori intermedi = miscela." },
  { path: "fragment.duration", label: "grano (s)", min: 0.001, max: 2, step: 0.001, def: 0.5, env: true, mode: "tendency",
    info: "Durata di ogni grano, in secondi. Come curva fa accelerare/rallentare il flusso (grani corti = tempo veloce)." },
  { path: "fragment.duration_range", label: "grano ± (s)", min: 0, max: 1, step: 0.001, def: 0, env: true, mode: "tendency",
    info: "Variazione casuale della durata del grano attorno al valore base. 0 = tutti i grani uguali." },
  { path: "fragment.rhythm.bpm", label: "bpm", min: 20, max: 300, step: 1, def: 120, env: true, mode: "rhythm",
    info: "Velocità del pattern ritmico. Come curva = accelerando/ritardando continui." },
  { path: "fragment.rhythm.pattern", label: "pattern", kind: "numlist", def: [0.25, 0.125, 0.125], mode: "rhythm",
    info: "Valori ritmici ciclici in frazioni di semibreve: 0.25 = semiminima (un movimento), 0.125 = croma, 0.0625 = semicroma. Separati da virgola." },
  { path: "time_mode", label: "time mode", kind: "select",
    options: ["absolute", "normalized"], def: "absolute",
    info: "Tempi degli envelope del layer: absolute = secondi; normalized = frazioni 0..1 scalate sulla durata (curve riusabili su layer di durate diverse)." },
  { path: "fragment.envelope", label: "inviluppo", kind: "select",
    options: ["raised_cosine", "rectangle"], def: "raised_cosine",
    info: "Forma d'ampiezza del grano: raised_cosine = campana morbida anti-click; rectangle = nessuna sagomatura (bordi netti)." },
  { path: "fragment.attack", label: "attack (s)", min: 0, max: 0.1, step: 0.001, def: 0.008,
    info: "Fade-in del grano in secondi (anti-click). Scalare nel motore." },
  { path: "fragment.release", label: "release (s)", min: 0, max: 0.1, step: 0.001, def: 0.01,
    info: "Fade-out del grano in secondi (anti-click). Scalare nel motore." },
  { path: "pointer.start", label: "pointer", min: 0, max: 1, step: 0.01, def: 0, env: true,
    info: "Punto di lettura nel file sorgente: 0 = inizio, 0.5 = metà, 1 = fine. Come curva attraversa il file lungo il brano (time-stretch granulare)." },
  { path: "pointer.start_range", label: "pointer ±", min: 0, max: 1, step: 0.01, def: 0, env: true,
    info: "Variazione casuale del punto di lettura. 0.5 con pointer 0.5 = ogni grano pesca ovunque nel file." },
  { path: "pointer.overflow", label: "overflow", kind: "select",
    options: ["clamp_back", "loop", "zero_pad"], def: "clamp_back",
    info: "Se il grano supera la fine del file: clamp_back arretra del minimo necessario; loop riparte dall'inizio; zero_pad completa con silenzio." },
  { path: "selection.strategy", label: "selezione", kind: "select",
    options: ["sequential", "rotation", "random"], def: "sequential",
    info: "Quale file suona ogni grano: sequential = in ordine alfabetico ciclando; rotation = permutazione casuale per giro (ogni file una volta); random = estrazioni indipendenti." },
  { path: "volume", label: "volume (dB)", min: -60, max: 12, step: 0.5, def: 0, env: true,
    info: "Guadagno del layer in dB, campionato al momento di posa di ogni grano. Come curva = crescendo/diminuendo." },
  { path: "volume_range", label: "volume ± (dB)", min: 0, max: 12, step: 0.5, def: 0, env: true,
    info: "Variazione casuale del volume per grano, in ±dB: respiro dinamico." },
  { path: "pan", label: "pan (°)", min: -360, max: 360, step: 1, def: 0, env: true,
    info: "Posizione stereo in gradi: 0 = centro, +45 = tutto a sinistra, −45 = tutto a destra. Spazio circolare: una curva sempre crescente fa RUOTARE il suono." },
  { path: "pan_range", label: "pan ± (°)", min: 0, max: 180, step: 1, def: 0, env: true,
    info: "Sparpagliamento stereo casuale attorno al pan, in ±gradi." },
];

/* Blocco digger (provision): usato solo col toggle "download (dig)".
   I campi quantitativi (durate, conteggi) li calcola il motore. */
const PROVISION_DEFS = [
  { path: "provision.search.license", label: "licenza", kind: "select",
    options: ["cc", "publicdomain", "cc-commercial", "any"], def: "cc",
    info: "Diritti d'uso dei file cercati su Internet Archive: cc = Creative Commons, publicdomain = pubblico dominio, cc-commercial = CC senza clausola NC, any = nessun filtro." },
  { path: "provision.search.collection", label: "collection", kind: "list", def: [],
    info: "Collezioni di Internet Archive in cui cercare (separate da virgola). Vuoto = tutte. Verifica che la collection esista: nomi sbagliati = zero risultati." },
  { path: "provision.search.subject", label: "subject", kind: "list", def: [],
    info: "Tag/argomenti degli item (separati da virgola), es. nature, ambient." },
  { path: "provision.search.query", label: "query lucene", kind: "text", def: "",
    info: "Via di fuga: sintassi Lucene grezza aggiunta alla ricerca. Es. format:(\"WAVE\" OR \"Flac\") per item che contengono file lossless." },
  { path: "provision.files.prefer", label: "formati", kind: "listlist",
    def: [["Flac", "WAVE", "AIFF"]],
    info: "Formati preferiti (separati da virgola, a pari merito). Il motore legge solo wav/aif/flac: niente mp3. Quanti file scaricare e le durate min/max li calcola l'analisi della partitura." },
];
const ALL_LAYER_DEFS = [...LAYER_DEFS, ...PROVISION_DEFS];

const state = { global: {}, layers: [] };
let layerCounter = 0;

function newControl(def, enabled = false) {
  return { enabled, value: def.def };
}

function newLayer() {
  layerCounter += 1;
  const params = {};
  for (const def of ALL_LAYER_DEFS) params[def.path] = newControl(def, def.path === "duration");
  return { layer_id: `layer${String(layerCounter).padStart(2, "0")}`,
           pool: "audio/pool/", params };
}

/* ---------- envelope editor ---------- */
function drawEnvelope(canvas, def, control, layerDur) {
  const ctx = canvas.getContext("2d");
  const W = canvas.width = canvas.clientWidth * 2;
  const H = canvas.height = 112;
  ctx.clearRect(0, 0, W, H);
  ctx.strokeStyle = "#eee";
  for (let i = 1; i < 4; i++) {
    ctx.beginPath(); ctx.moveTo(0, H * i / 4); ctx.lineTo(W, H * i / 4); ctx.stroke();
  }
  const pts = control.value;
  ctx.strokeStyle = "#111"; ctx.fillStyle = "#111"; ctx.lineWidth = 2;
  ctx.beginPath();
  pts.forEach(([t, v], i) => {
    const x = (t / layerDur) * W;
    const y = H - ((v - def.min) / (def.max - def.min)) * H;
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.stroke();
  pts.forEach(([t, v]) => {
    const x = (t / layerDur) * W;
    const y = H - ((v - def.min) / (def.max - def.min)) * H;
    ctx.beginPath(); ctx.arc(x, y, 5, 0, 7); ctx.fill();
  });
}

function attachEnvelopeEditor(canvas, def, control, getDur) {
  const toPoint = (ev) => {
    const r = canvas.getBoundingClientRect();
    const t = Math.max(0, Math.min(1, (ev.clientX - r.left) / r.width)) * getDur();
    const v = def.min + Math.max(0, Math.min(1, 1 - (ev.clientY - r.top) / r.height)) * (def.max - def.min);
    return [Number(t.toFixed(3)), Number(v.toFixed(4))];
  };
  const nearest = (ev) => {
    const r = canvas.getBoundingClientRect();
    let best = -1, bestD = 14;
    control.value.forEach(([t, v], i) => {
      const x = (t / getDur()) * r.width;
      const y = r.height - ((v - def.min) / (def.max - def.min)) * r.height;
      const d = Math.hypot(x - (ev.clientX - r.left), y - (ev.clientY - r.top));
      if (d < bestD) { bestD = d; best = i; }
    });
    return best;
  };
  let dragging = -1;
  const redraw = () => drawEnvelope(canvas, def, control, getDur());
  canvas.addEventListener("pointerdown", (ev) => {
    const hit = nearest(ev);
    if (ev.button === 2 || ev.detail === 2) {           // destro/doppio: rimuovi
      if (hit >= 0 && control.value.length > 2) { control.value.splice(hit, 1); redraw(); }
      return;
    }
    if (hit >= 0) { dragging = hit; }
    else { control.value.push(toPoint(ev));
           control.value.sort((a, b) => a[0] - b[0]);
           dragging = control.value.findIndex(p => p[0] === toPoint(ev)[0]); }
    canvas.setPointerCapture(ev.pointerId);
    redraw();
  });
  canvas.addEventListener("pointermove", (ev) => {
    if (dragging < 0) return;
    control.value[dragging] = toPoint(ev);
    control.value.sort((a, b) => a[0] - b[0]);
    redraw();
  });
  canvas.addEventListener("pointerup", () => { dragging = -1; });
  canvas.addEventListener("contextmenu", (ev) => ev.preventDefault());
  redraw();
}

/* ---------- righe parametro ---------- */
function paramRow(def, control, getDur) {
  const row = document.createElement("div");
  row.className = "param" + (control.enabled ? "" : " off");

  const chk = document.createElement("input");
  chk.type = "checkbox"; chk.checked = control.enabled;
  chk.onchange = () => { control.enabled = chk.checked; row.classList.toggle("off", !chk.checked); };

  const name = document.createElement("span");
  name.className = "name"; name.textContent = def.label;
  name.title = "clicca per la spiegazione";
  name.onclick = () => showInfo(def);

  const slot = document.createElement("span");
  const val = document.createElement("span"); val.className = "value";

  const showScalar = () => {
    slot.innerHTML = ""; val.textContent = "";
    if (def.kind === "select") {
      const sel = document.createElement("select");
      for (const o of def.options) {
        const opt = document.createElement("option");
        opt.value = o; opt.textContent = o;
        if (String(o) === String(control.value)) opt.selected = true;
        sel.append(opt);
      }
      sel.onchange = () => { control.value = def.options[sel.selectedIndex]; };
      slot.append(sel);
    } else if (def.kind === "int") {
      const num = document.createElement("input");
      num.type = "number"; num.value = control.value;
      num.onchange = () => { control.value = parseInt(num.value, 10) || 0; };
      slot.append(num);
    } else if (def.kind === "numlist") {
      const txt = document.createElement("input");
      txt.type = "text";
      txt.value = (control.value || []).join(", ");
      txt.placeholder = "es. 0.25, 0.125, 0.125";
      txt.onchange = () => {
        control.value = txt.value.split(",").map(s => parseFloat(s.trim()))
                                 .filter(n => !isNaN(n) && n > 0);
      };
      slot.append(txt);
    } else if (def.kind === "text" || def.kind === "list" || def.kind === "listlist") {
      const txt = document.createElement("input");
      txt.type = "text";
      txt.value = def.kind === "text" ? (control.value || "")
                : def.kind === "list" ? (control.value || []).join(", ")
                : (control.value?.[0] || []).join(", ");
      txt.placeholder = def.kind === "text" ? "" : "voci separate da virgola";
      txt.onchange = () => {
        const items = txt.value.split(",").map(s => s.trim()).filter(Boolean);
        control.value = def.kind === "text" ? txt.value.trim()
                      : def.kind === "list" ? items : [items];
      };
      slot.append(txt);
    } else {
      const rng = document.createElement("input");
      rng.type = "range"; rng.min = def.min; rng.max = def.max; rng.step = def.step;
      rng.value = Array.isArray(control.value) ? def.def : control.value;
      val.textContent = rng.value;
      rng.oninput = () => { control.value = parseFloat(rng.value); val.textContent = rng.value; };
      slot.append(rng);
    }
  };

  row.append(chk, name, slot, val);

  if (def.env) {
    const envBtn = document.createElement("button");
    envBtn.className = "envbtn"; envBtn.textContent = "env"; envBtn.title = "curva nel tempo";
    let envRow = null;
    const openEditor = () => {
      envBtn.classList.add("on");
      if (!Array.isArray(control.value))
        control.value = [[0, control.value], [getDur(), control.value]];
      slot.innerHTML = ""; val.textContent = "curva";
      envRow = document.createElement("div");
      envRow.className = "envrow";
      const cv = document.createElement("canvas");
      cv.className = "envelope";
      envRow.append(cv);
      row.after(envRow);
      attachEnvelopeEditor(cv, def, control, getDur);
    };
    envBtn.onclick = () => {
      if (envBtn.classList.contains("on")) {
        envBtn.classList.remove("on");
        control.value = control.value[0][1];
        if (envRow) envRow.remove();
        showScalar();
      } else openEditor();
    };
    name.append(" ", envBtn);
    if (Array.isArray(control.value)) { showScalar(); queueMicrotask(openEditor); }
    else showScalar();
  } else showScalar();

  return row;
}

/* ---------- pannelli ---------- */
function renderGlobals() {
  const box = document.getElementById("global-params");
  box.innerHTML = "";
  for (const def of GLOBAL_DEFS) {
    if (!state.global[def.path]) state.global[def.path] = newControl(def);
    box.append(paramRow(def, state.global[def.path], () => 60));
  }
}

function renderLayers() {
  const main = document.getElementById("layers");
  main.innerHTML = "";
  state.layers.forEach((layer, idx) => {
    const panel = document.createElement("section");
    panel.className = "panel";
    const head = document.createElement("div");
    head.className = "layer-head";
    const id = document.createElement("input");
    id.type = "text"; id.value = layer.layer_id;
    id.onchange = () => { layer.layer_id = id.value; };
    const pool = document.createElement("input");
    pool.type = "text"; pool.value = layer.pool; pool.title = "pool";
    pool.onchange = () => { layer.pool = pool.value; };
    // Modalità grano: continua (tendency) o ritmica (bpm+pattern),
    // mutuamente esclusive nel motore.
    const isRhythm = () => layer.params["fragment.rhythm.pattern"]?.enabled
                        || layer.params["fragment.rhythm.bpm"]?.enabled;
    const mode = document.createElement("select");
    for (const [v, l] of [["tendency", "grano continuo"], ["rhythm", "modalità ritmica"]]) {
      const o = document.createElement("option");
      o.value = v; o.textContent = l;
      if ((v === "rhythm") === !!isRhythm()) o.selected = true;
      mode.append(o);
    }
    mode.onchange = () => {
      const rhythm = mode.value === "rhythm";
      for (const p of ["fragment.duration", "fragment.duration_range"])
        layer.params[p].enabled = false;
      for (const p of ["fragment.rhythm.bpm", "fragment.rhythm.pattern"])
        layer.params[p].enabled = rhythm;
      if (!rhythm) layer.params["fragment.duration"].enabled = true;
      renderLayers();
    };
    const flags = document.createElement("span");
    for (const flag of ["solo", "mute"]) {
      if (!layer.params[flag]) layer.params[flag] = { enabled: false, value: true };
      const lab = document.createElement("label");
      lab.className = "toggle";
      const chk = document.createElement("input");
      chk.type = "checkbox"; chk.checked = layer.params[flag].enabled;
      chk.onchange = () => { layer.params[flag] = { enabled: chk.checked, value: true }; };
      lab.append(chk, ` ${flag}`);
      flags.append(lab);
    }
    const del = document.createElement("button");
    del.className = "danger"; del.textContent = "×";
    del.onclick = () => { state.layers.splice(idx, 1); renderLayers(); };
    head.append(id, pool, mode, flags, del);
    panel.append(head);
    const grid = document.createElement("div");
    grid.className = "params";
    const getDur = () => {
      const d = layer.params["duration"];
      return (d.enabled && !Array.isArray(d.value)) ? d.value : 20;
    };
    const grainMode = isRhythm() ? "rhythm" : "tendency";
    for (const def of LAYER_DEFS) {
      if (!layer.params[def.path]) layer.params[def.path] = newControl(def);
      if (def.mode && def.mode !== grainMode) continue;
      grid.append(paramRow(def, layer.params[def.path], getDur));
    }
    panel.append(grid);
    const digTitle = document.createElement("h2");
    digTitle.textContent = "digger";
    digTitle.style.margin = "1rem 0 .6rem";
    const digGrid = document.createElement("div");
    digGrid.className = "params";
    for (const def of PROVISION_DEFS) {
      if (!layer.params[def.path]) layer.params[def.path] = newControl(def);
      digGrid.append(paramRow(def, layer.params[def.path], getDur));
    }
    panel.append(digTitle, digGrid);
    main.append(panel);
  });
}

/* ---------- pannello info ---------- */
function showInfo(def) {
  const box = document.getElementById("infobox");
  box.querySelector("h3").textContent = def.label;
  box.querySelector("p").textContent = def.info || "nessuna descrizione";
  box.hidden = false;
}

/* ---------- azioni ---------- */
const status = (msg, err) => {
  const el = document.getElementById("status");
  el.textContent = msg; el.classList.toggle("error", !!err);
};

async function doRender() {
  status("render in corso…");
  document.getElementById("player").hidden = true;
  document.getElementById("btn-download").hidden = true;
  const dig = document.getElementById("chk-dig").checked;
  const res = await fetch("/api/render", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ state, dig }),
  });
  const { job_id } = await res.json();
  const poll = setInterval(async () => {
    const s = await (await fetch(`/api/jobs/${job_id}`)).json();
    if (s.state === "running") { status(dig ? "download + render…" : "render…"); return; }
    clearInterval(poll);
    if (s.state === "error") { status(`errore: ${s.detail}`, true); return; }
    status("fatto");
    const url = `/api/jobs/${job_id}/audio`;
    const player = document.getElementById("player");
    player.src = url; player.hidden = false; player.play().catch(() => {});
    const dl = document.getElementById("btn-download");
    dl.href = url; dl.hidden = false;
  }, 500);
}

async function doExport() {
  const res = await fetch("/api/yaml", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ state }),
  });
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = "score.yaml"; a.click();
}

async function doImport(file) {
  const text = await file.text();
  const res = await fetch("/api/import", {
    method: "POST", headers: { "Content-Type": "text/yaml" }, body: text,
  });
  const imported = await res.json();
  state.global = {};
  for (const def of GLOBAL_DEFS)
    state.global[def.path] = imported.global[def.path] ?? newControl(def);
  state.layers = imported.layers.map((l) => {
    const layer = newLayer();
    layer.layer_id = l.layer_id; layer.pool = l.pool;
    for (const def of ALL_LAYER_DEFS)
      layer.params[def.path] = l.params[def.path] ?? newControl(def);
    for (const [path, ctl] of Object.entries(l.params))
      if (!layer.params[path]) layer.params[path] = ctl;  // solo, mute, extra
    return layer;
  });
  renderGlobals(); renderLayers();
  status("yaml importato");
}

document.getElementById("btn-add-layer").onclick = () => {
  state.layers.push(newLayer()); renderLayers();
};
document.getElementById("btn-render").onclick = doRender;
document.getElementById("btn-export").onclick = doExport;
document.getElementById("file-import").onchange = (ev) => {
  if (ev.target.files[0]) doImport(ev.target.files[0]);
};

state.layers.push(newLayer());
renderGlobals();
renderLayers();
