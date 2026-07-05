---
slug: yaml
type: reference
status: stable
tags: [yaml, syntax, parameters, envelopes, tendency-masks]
sources:
  - audiolayers/engine/render.py
  - audiolayers/parameters/
  - audiolayers/envelopes/
  - audiolayers/strategies/
  - audiolayers/provisioning/
  - audiolayers/shared/seeding.py
---

# YAML Reference — audiolayers

Reference completa del formato di partitura consumato da `python -m audiolayers.main`.
Per la riga di comando vedi [cli.md](cli.md); per le decisioni di design il
[plan di bootstrap](../plans/done/2026-07-02-001-project-bootstrap-plan.md).

## Partitura minima

```yaml
layers:
  - layer_id: "unico"
    duration: 30.0
    pool: "audio/"
    fragment:
      duration: 0.5
```

## Chiavi top-level

| Chiave | Default | Significato |
|---|---|---|
| `sample_rate` | `48000` | SR di progetto; le sorgenti vengono ricampionate in ingresso (soxr VHQ) |
| `seed` | assente | riproducibilità: stesso seed → render bit-identico. Assente → generato dal timestamp e **sempre loggato** con l'istruzione per riprodurlo |
| `master_volume` | `0.0` | dB sul mix finale; scalare o envelope (curva per-campione) |
| `layers` | richiesto | lista dei layer (si sommano nel mix stereo) |

## Sintassi dei parametri

Ogni parametro numerico accetta tre forme:

| Forma | Esempio | Comportamento |
|---|---|---|
| Scalare | `volume: -6.0` | valore fisso |
| Envelope | `volume: [[0, -24], [30, 0]]` | breakpoint `[tempo, valore]`, interpolazione lineare, hold oltre i bordi, ordinamento automatico |
| Dict | `volume: {points: [[0, -24], [1, 0]], time_mode: normalized}` | opzioni esplicite per-envelope |

`time_mode: absolute` (default, secondi) oppure `normalized` (tempi in
`[0, 1]` scalati sulla `duration` del layer). Dichiarabile a livello di layer
(vale per tutti i suoi envelope) o localmente nella forma dict (vince).

### Tendency mask (base ± range)

Ogni parametro può avere una sorella `_range`: il valore per-frammento è
estratto uniformemente in `[base(t) − range(t), base(t) + range(t)]`
(modello Truax). Base e range sono entrambi envelope-abili: la maschera
respira nel tempo. `range` assente o `0` → deterministico.

```yaml
volume: -6.0
volume_range: 3.0            # ±3 dB per frammento
pan: [[0, 0], [60, 360]]     # il centro della maschera ruota
pan_range: 15.0              # ±15° di sparpagliamento intorno al centro
```

## Chiavi di layer

| Chiave | Default | Significato |
|---|---|---|
| `layer_id` | `"layer"` | nome (namespacing del seed: cambia nome → cambiano i draw) |
| `onset` | `0.0` | inizio del layer sulla timeline globale (secondi) |
| `duration` | richiesto | durata-obiettivo; l'ultimo frammento non viene mai mozzato, quindi il layer può sforare |
| `pool` | richiesto | cartella con i file sorgente (wav/aif/aiff/flac); mono al SR di progetto in ingresso, stereo downmixati |
| `solo` | — | se almeno un layer è in solo, suonano solo quelli |
| `mute` | — | esclude il layer (ignorato se c'è un solo attivo) |
| `provision` | — | ricerca Internet Archive per `--dig` (vedi sotto) |
| `time_mode` | `absolute` | default per gli envelope del layer |

### Spaziatura: `fill_factor` e `distribution`

```yaml
fill_factor: 1.0        # IOI = durata_frammento / F
distribution: 0.0       # 0 = metronomo, 1 = asincrono (uniforme 0..2×IOI)
```

- `fill_factor` = 1 → frammenti back-to-back; < 1 → silenzi; > 1 →
  sovrapposizione (gli inviluppi producono crossfade emergenti).
- `distribution` è il blend lineare Truax tra IOI sincrono e asincrono
  fino a 1; da 1 a 2 lo spread asincrono si amplifica (uniforme
  0..2×IOI×d): grappoli e buchi via via più marcati.
- Entrambi envelope-abili: `fill_factor: [[0, 0.5], [60, 3.0]]` infittisce
  il tessuto lungo il brano.

### Blocco `fragment`

```yaml
fragment:
  duration: 0.5          # apertura (s) — tendency mask
  duration_range: 0.2
  # E/O la griglia ritmica (componibili: rhythm decide QUANDO nasce
  # un grano, duration QUANTO dura; senza duration il grano riempie lo slot):
  rhythm:
    bpm: 120             # scalare o envelope (accelerando/ritardando)
    pattern: [0.25, 0.125, 0.125, 0.5]   # frazioni di semibreve, ciclico
  envelope: raised_cosine  # | rectangle (nessun inviluppo)
  attack: 0.008            # s, fade-in anti-click
  release: 0.010           # s, fade-out
```

Convenzione ritmica: `0.25` = semiminima = un movimento = `60/bpm` secondi.

### Blocco `pointer`

```yaml
pointer:
  start: 0.5             # [0,1] → posizione assoluta nel file (0.5 = metà),
  start_range: 0.1       #         indipendente dalla durata del frammento
  overflow: clamp_back   # | loop | zero_pad
```

Overflow (quando `start + durata` supera la fine del file):
`clamp_back` arretra del minimo necessario (default); `loop` riparte
dall'inizio; `zero_pad` completa con silenzio.

### Blocco `selection`

```yaml
selection:
  strategy: sequential   # | rotation | random
```

`sequential` = in ordine alfabetico, ciclando; `rotation` = permutazione
casuale per giro (ogni file una volta per giro); `random` = estrazioni
indipendenti.

### Blocco `provision` (opzionale, solo con `--dig`)

```yaml
provision:
  mode: per-fragment       # | threshold | fixed (quanti file garantire)
  count: 20                # fixed: esatti; threshold: minimo
  variety: 0.5             # threshold: frazione del fabbisogno (0..1)
  min_margin: 1.5          # margine sulla durata minima richiesta
  max_factor: 20           # durata max file = min x fattore (mai < 10 s)
  search:                  # qualunque campo di ricerca archivedigger
    collection: [field-recordings]
    license: cc            # default se omesso
  files:
    prefer:
      - [Flac, WAVE, AIFF] # default se omesso (il loader non legge mp3)
```

Il blocco può vivere anche **a livello di partitura** (digger globale):
in quel caso i blocchi dei layer vengono ignorati, i fabbisogni dei
layer che condividono un pool si sommano e la policy si applica
all'aggregato.

Senza `--dig` il blocco è ignorato e il pool resta una normale cartella
locale. Con `--dig` orienta la ricerca su Internet Archive; i campi
quantitativi (`max_items`, `filters.min/max_duration`,
`max_files_per_item`) sono **calcolati** dall'analisi della partitura e
non dichiarabili. Dettagli in [cli.md](cli.md#--dig-provisioning-automatico-del-pool).

### Uscita del frammento

```yaml
volume: 0.0              # dB (tendency mask con volume_range)
pan: 0.0                 # gradi: 0 = centro, +45 = tutto L, −45 = tutto R
pan_range: 0.0           # spazio circolare (mod 360): un envelope di pan
                         # crescente senza limiti fa RUOTARE il suono
```

Pan mid/side a potenza costante: `L² + R² = s²` a ogni angolo.

## Tabella bounds

| Parametro | Min | Max | Max range |
|---|---|---|---|
| `fill_factor` | 0.001 | 50 | 25 |
| `distribution` | 0 | 2 | 2 |
| `fragment.duration` | 0.001 | 600 | 300 |
| `pointer.start` | 0 | 1 | 1 |
| `volume` | −120 | 12 | 24 |
| `pan` | −∞ | +∞ | ∞ |
| `master_volume` | −120 | 12 | — |

Valori fuori bounds → `ParameterBoundError` al parse (anche sui breakpoint
degli envelope): la partitura non parte, niente sorprese silenziose.

## Riproducibilità (seeding namespaced)

Ogni componente stocastica ha un RNG derivato da
`sha256(seed : layer_id : componente)`: i draw di un layer/parametro non
dipendono da cosa fanno gli altri. Conseguenze pratiche: `solo`/`mute` non
alterano il suono dei layer superstiti; aggiungere un parametro non cambia
gli altri; ogni strategia è testabile in isolamento.

## Esempio completo

```yaml
sample_rate: 48000
seed: 424242
master_volume: [[0, 0], [120, -6]]

layers:
  - layer_id: "tappeto"
    onset: 0.0
    duration: 120.0
    pool: "audio/paesaggi/"
    fill_factor: [[0, 0.6], [120, 2.0]]
    distribution: 0.3
    fragment: {duration: 1.2, duration_range: 0.4}
    pointer: {start: [[0, 0], [120, 1]], start_range: 0.05, overflow: loop}
    volume: -12.0
    volume_range: 3.0
    pan: 0.0
    pan_range: 40.0

  - layer_id: "ritmo"
    onset: 30.0
    duration: 60.0
    pool: "audio/percussioni/"
    selection: {strategy: rotation}
    fragment:
      rhythm: {bpm: [[0, 90], [60, 140]], pattern: [0.125, 0.0625, 0.0625]}
      attack: 0.003
      release: 0.005
    volume: -6.0
    pan: [[0, -30], [60, 30]]
```
