---
slug: project-bootstrap
type: plan
status: done
created: 2026-07-02
completed: 2026-07-02
tags: [bootstrap, architettura, yaml, tdd]
---

# Plan — Bootstrap del progetto audiolayers

## Contesto

**audiolayers** è un ambiente compositivo dichiarativo per Computer Music in
Python. Legge una collezione di file audio e, seguendo una partitura YAML,
dispone frammenti dei file lungo il tempo, controllando per ciascuno (o per
tutti): apertura (durata), punto di lettura, gain, pan.

Il progetto eredita deliberatamente l'architettura e le convenzioni YAML di
[PythonGranularEngine](https://github.com/DMGiulioRomano/PythonGranularEngine)
(PGE), operando però a una scala temporale diversa: PGE granula a livello di
micro-suono (grani ~50 ms), audiolayers dispone **frammenti di file interi**
(macro-forma). La mappatura concettuale: `stream → layer`, `grain → fragment`,
`pointer.start → punto di lettura`, `grain.duration → apertura`.

Fondamento teorico: le **tendency masks** di Barry Truax (POD/PODX, *Real-Time
Granular Synthesis with a Digital Signal Processor*, CMJ 12(2), 1988) — ogni
parametro è `base(t) ± range(t)` con base e range envelope-abili (ramp lineari
a breakpoint), estrazione uniforme entro la banda.

## Registro delle decisioni di design

Esito dell'intervista di design (sessione del 2026-07-02):

| # | Decisione |
|---|-----------|
| D1 | **Output**: rendering offline su singolo file audio. Default WAV float32; `--format {wav,aiff,flac}`, `--bit-depth 24` per PCM. |
| D2 | **Modello di spaziatura**: `fill_factor` (F) governa l'IOI: `IOI = durata_frammento / F`. F=1 concatenazione, F<1 silenzi, F>1 sovrapposizione. Envelope-abile. |
| D3 | **`distribution`** ∈ [0,1] (modello Truax, stesso nome di PGE): 0 = sync (IOI deterministico), 1 = async (uniform 0..2×IOI medio), blend lineare intermedio. Envelope-abile. |
| D4 | **Generazione onset separata dal rendering**: i generatori di onset sono Strategy intercambiabili; producono N onset allineati per indice alla lista di N frammenti → interpolabili linearmente tra loro. |
| D5 | **Parametri = tendency mask**: ogni parametro numerico è `base ± range`, entrambi scalare-o-envelope. `range=0` → deterministico. Convenzione YAML: chiavi sorelle `param` / `param_range` (come PGE). |
| D6 | **Pool e selezione**: la partitura punta a cartella/glob/lista; strategie di selezione `sequential`, `rotation`, `random` — Strategy pluggable, combinabili (miscela probabilistica pesata) e modulabili nel tempo. |
| D7 | **N frammenti da durata-obiettivo**: si pesca finché serve; **nessun frammento viene mozzato** — ci si ferma quando il prossimo onset supererebbe la durata-obiettivo; l'ultimo frammento suona intero e può sforare. |
| D8 | **Apertura (durata frammento)**: modello unificato tendency mask (regolare = range 0, casuale = range > 0, entrambi modulabili) + Strategy `rhythmic` separata (pattern ciclico di valori su BPM). |
| D9 | **Punto di lettura**: normalizzato [0,1] → posizione assoluta `punto × len_file` (indipendente dalla durata del frammento). Overflow come Strategy: `clamp_back` (default), `loop`, `zero_pad`. |
| D10 | **Gain in dB** (`volume`/`volume_range` come PGE). |
| D11 | **Inviluppo per-frammento** (anti-click) come Strategy: default raised-cosine, attack/release ~5–10 ms. Con F>1 l'overlap + inviluppi produce crossfade emergenti. |
| D12 | **Stereo mid/side**: `mid = s·cos(rad)`, `side = s·sin(rad)`, `L = (mid+side)/√2`, `R = (mid−side)/√2`, `rad = gradi·π/180`. Pan in gradi, range infinito (mod 360 assorbito dalle trigonometriche), `+` = sinistra, 0 = centro, ±45° = tutto L/R. Sorgenti downmixate a mono in ingresso. |
| D13 | **Sample rate di progetto**: default 48000, dichiarabile nel YAML; resampling in ingresso con `soxr` (fallback `scipy.signal.resample_poly`). Interno: NumPy float64/32 in [−1,1]. |
| D14 | **Seeding namespaced ovunque** (lezione da PGE issue #154): RNG derivato per componente — `numpy.random.default_rng` da `SeedSequence` + spawn nominato per `(seed, layer_id, component)`. MAI un RNG globale condiviso. Seed assente → generato da timestamp e **sempre loggato** (stdout + sidecar). Override `--seed`. |
| D15 | **Multi-layer**: lista `layers:` nel YAML; ogni layer è una sequenza indipendente col modello completo; il renderer somma i layer sulla timeline stereo. `solo`/`mute` per layer. |
| D16 | **Master**: `master_volume` (dB, envelope-abile) + misura e report del picco a fine render (`peak dBFS` / `CLIPPING +x dB`). `--normalize` opzionale, mai default. |
| D17 | **Strategy pattern come vincolo architetturale**: ogni famiglia di algoritmi intercambiabili → interfaccia (ABC/Protocol) + implementazioni concrete + registry. Blend di strategie = a sua volta una Strategy. |
| D18 | **Sistema parametri a 3 livelli** (da PGE): `parameter_definitions.py` (bounds), `parameter_schema.py` (ParameterSpec: yaml_path, default, range_path, exclusive_group), `parser.py` (raw → Parameter validato). Parametri assenti nel YAML → inizializzati al default dello schema. |
| D19 | **Test**: quattro livelli — unit (ogni Strategy in isolamento), integration (pipeline combinate), golden (render fixture vs riferimento con tolleranza), e2e (CLI reale). |
| D20 | Repo GitHub pubblico `audiolayers`, licenza MIT (Domenico Nasso), cartelle `docs/`, `src/`, `tests/`. |

## Architettura

```
src/
├── main.py                  # CLI: audiolayers render score.yaml [flags]
├── engine/
│   └── generator.py         # YAML → List[Layer]; solo/mute; seed di sessione
├── core/
│   ├── layer.py             # Layer: costruzione sequenza frammenti (D7)
│   ├── fragment.py          # Fragment: (source, read_point, duration, gain, pan, envelope)
│   └── layer_config.py      # config di processo per-layer
├── parameters/              # ereditato da PGE (D18), con RNG iniettato (D14)
│   ├── parameter_definitions.py   # ParameterBounds registry
│   ├── parameter_schema.py        # ParameterSpec registry (default, yaml_path, _range)
│   ├── parameter.py               # Smart Parameter: get_value(t) = base±range gated+clamped
│   ├── parser.py                  # raw YAML → Parameter (validazione bounds)
│   ├── parameter_factory.py
│   └── exclusive_selector.py      # gruppi mutuamente esclusivi
├── envelopes/               # ereditato da PGE, inizialmente semplificato
│   ├── envelope.py                # breakpoints, evaluate(t), time_mode
│   ├── envelope_builder.py        # scalare | [[t,v],…] | dict {type, points}
│   └── envelope_interpolation.py  # linear (v1); cubic/step (v2)
├── strategies/
│   ├── selection_strategy.py      # sequential | rotation | random | blend (D6)
│   ├── duration_strategy.py       # tendency | rhythmic (D8)
│   ├── onset_strategy.py          # fill_factor + distribution (D2, D3)
│   ├── overflow_strategy.py       # clamp_back | loop | zero_pad (D9)
│   └── fragment_envelope.py       # raised_cosine | … (D11)
├── audio/
│   ├── pool.py                    # scansione cartella/glob, caricamento
│   ├── source_loader.py           # soundfile + resampling soxr + downmix mono (D13)
│   └── pan.py                     # mid/side constant-power (D12)
├── rendering/
│   ├── timeline_renderer.py       # somma frammenti su buffer stereo (N,2)
│   ├── master.py                  # master_volume, peak report, normalize (D16)
│   └── writer.py                  # WAV/AIFF/FLAC via soundfile (D1)
└── shared/
    ├── seeding.py                 # SeedSequence spawn nominato (D14)
    ├── exceptions.py              # MissingFieldError, ParameterBoundError, …
    └── logger.py
```

## Schema YAML (bozza v0)

```yaml
sample_rate: 48000        # opzionale (default 48000)
seed: 42                  # opzionale; assente → timestamp, loggato
master_volume: 0.0        # dB, envelope-abile

layers:
  - layer_id: "fondale"
    onset: 0.0                 # inizio del layer sulla timeline globale (sec)
    duration: 180.0            # durata-obiettivo (sec) — criterio di stop D7
    pool: "audio/paesaggi/"    # cartella | glob | lista di file
    # solo:  /  mute:          # flag come PGE

    selection:
      strategy: sequential     # sequential | rotation | random
      # blend futuro: {strategy: blend, components: [...], weights: [...]}

    fill_factor: 1.0           # F (D2), envelope-abile: [[0, 0.5], [180, 2.0]]
    distribution: 0.0          # 0=sync 1=async (D3), envelope-abile

    fragment:
      duration: 0.5            # apertura — tendency mask (D8)
      duration_range: 0.2
      # oppure:
      # rhythm: {bpm: 120, pattern: [0.25, 0.125, 0.125, 0.5]}
      envelope: raised_cosine  # inviluppo anti-click (D11)
      attack: 0.008
      release: 0.010

    pointer:
      start: 0.5               # [0,1] normalizzato sul file sorgente (D9)
      start_range: 0.1
      overflow: clamp_back     # clamp_back | loop | zero_pad

    volume: -6.0               # dB (D10)
    volume_range: 3.0
    pan: 0.0                   # gradi, mod 360, + = sinistra (D12)
    pan_range: 15.0
```

Regole trasversali (da PGE): ogni parametro numerico accetta scalare o
envelope `[[t, v], …]` (interpolazione lineare) o dict `{type, points,
time_mode}`; `time_mode: normalized` mappa i tempi su `duration`; parametri
assenti → default dallo schema; gruppi esclusivi (es. `fragment.duration` vs
`fragment.rhythm`) gestiti da `ExclusiveGroupSelector` con priorità.

## Roadmap TDD (tracer bullet)

Ogni milestone è una fetta verticale che chiude con suite verde. Workflow:
branch `feat/…` → red → green → refactor → merge (regole in
`~/.claude/rules/git-workflow.md`).

- **M0 — Scaffold** *(questo plan)*: struttura cartelle, venv, pytest,
  Makefile, smoke test dell'ambiente, repo GitHub.
- **M1 — Walking skeleton**: `render(score.yaml) → out.wav` per il caso
  minimo assoluto: 1 layer, 1 file sorgente fixture (sinusoide generata),
  selection sequential, duration fissa, F=1, distribution=0, niente random.
  E2E che verifica esistenza, durata e sample rate dell'output. Qui nascono
  (in forma minima): Envelope (scalare), Parameter, pool, timeline renderer
  mono→stereo, writer, CLI.
- **M2 — Envelope completo**: breakpoints `[[t,v],…]`, forma dict, evaluate,
  time_mode. Unit test su valori interpolati.
- **M3 — Sistema parametri**: definitions/schema/parser, bounds, default,
  `_range`, RNG namespaced iniettato. Unit test: default da schema, clipping,
  riproducibilità per-componente (stesso seed → stessi valori, componenti
  indipendenti).
- **M4 — Generatori di durata**: tendency mask + rhythmic. Unit.
- **M5 — Generatori di onset**: fill_factor + distribution + criterio di
  stop D7 (no mozzatura). Unit + property (mai frammenti oltre l'onset
  consentito; ultimo intero).
- **M6 — Selezione dal pool**: sequential/rotation/random (+ semantica del
  numero di pescate). Unit.
- **M7 — Lettura sorgente**: read_point normalizzato + overflow strategies
  (clamp_back/loop/zero_pad), resampling, downmix. Unit + integration con
  fixture audio corte.
- **M8 — Voce del frammento**: gain dB, inviluppo raised-cosine, pan
  mid/side. Unit (constant-power: L²+R²=s² a ogni angolo).
- **M9 — Mix multi-layer + master**: somma su timeline, solo/mute,
  master_volume, peak report, --normalize. Integration.
- **M10 — Golden + docs**: render di 2–3 partiture fixture confrontati con
  riferimenti (tolleranza float); `docs/reference/yaml.md` sul modello PGE;
  CHANGELOG se si decide di adottarlo.

## CLI (v1)

```
python -m src.main SCORE.yaml [-o OUT] [--format wav|aiff|flac]
                              [--bit-depth 24|32f] [--seed N]
                              [--normalize] [--verbose]
```

## Dipendenze

`numpy`, `soundfile`, `soxr` (fallback `scipy`), `PyYAML`; dev: `pytest`.
Python ≥ 3.12 (venv in `.venv`).

## Riferimenti

- PGE — architettura parametri, envelope, convenzioni YAML:
  <https://github.com/DMGiulioRomano/PythonGranularEngine>
- Lezione sul seeding: issue
  [PGE#154](https://github.com/DMGiulioRomano/PythonGranularEngine/issues/154)
- B. Truax, *Real-Time Granular Synthesis with a DSP*, CMJ 12(2), 1988.
