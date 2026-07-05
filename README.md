# audiolayers

[![CI](https://github.com/MU-prj/audiolayers/actions/workflows/ci.yml/badge.svg)](https://github.com/MU-prj/audiolayers/actions/workflows/ci.yml)

Ambiente compositivo dichiarativo per Computer Music. Legge una collezione di
file audio e, seguendo una partitura YAML, dispone frammenti dei file lungo il
tempo — controllando per ciascuno (o per tutti) apertura, punto di lettura,
gain e pan, secondo il modello delle *tendency masks* di Barry Truax
(`base ± range`, entrambi envelope-abili).

## Concetti chiave

- **Layer**: una sequenza indipendente di frammenti; più layer si sommano nel
  mix stereo finale (`solo`/`mute` per layer).
- **fill_factor** (F): governa la spaziatura — `IOI = durata_frammento / F`.
  F=1 concatenazione, F<1 silenzi, F>1 sovrapposizione (con crossfade
  emergenti dagli inviluppi).
- **distribution** ∈ [0,1]: da sincrono (metronomo) ad asincrono (stocastico),
  blend continuo, modello Truax.
- **Riproducibilità**: seed namespaced per componente; seed di sessione
  generato da timestamp e sempre loggato.

## Quickstart

```yaml
# brano.yaml
seed: 42
layers:
  - layer_id: "nuvola"
    duration: 30.0
    pool: "audio/"                          # cartella coi tuoi file
    fill_factor: [[0, 0.6], [30, 2.5]]      # da rado a denso
    distribution: 1.0                       # nuvola asincrona
    fragment: {duration: 0.3, duration_range: 0.15}
    volume: -9.0
    volume_range: 4.0
    pan_range: 60.0
```

```bash
python -m audiolayers.main brano.yaml -o brano.wav
```

**Manuale completo**: [docs/manuale.md](docs/manuale.md) — con la guida
passo-passo "Come scrivere uno YAML". Reference:
[docs/reference/yaml.md](docs/reference/yaml.md) ·
[docs/reference/cli.md](docs/reference/cli.md)

## Stato

Motore v1 completo (M0–M10): multi-layer, tendency masks su tutti i
parametri, strategie di durata/selezione/overflow/inviluppo, mix con
master envelope e report del picco. Suite: 185 test (unit, integration,
golden, e2e), motore di sintesi al 100% di copertura riga+ramo, eseguiti in
CI a ogni push/PR. Le decisioni di design (D1–D20) sono nel
[plan di bootstrap](docs/plans/done/2026-07-02-001-project-bootstrap-plan.md).

Questo repo contiene il **solo motore**, installabile come pacchetto
(`pip install git+https://github.com/MU-prj/audiolayers@main`). La GUI
web vive in [MU-prj/audiolayers_gui](https://github.com/MU-prj/audiolayers_gui)
e consuma il motore come libreria.

## Setup

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows
# .venv/bin/pip install -r requirements.txt     # POSIX
```

## Test

```bash
make tests            # suite completa
# oppure sottoinsiemi:
make unit             # solo unit
make integration      # solo integration
make golden           # confronto coi riferimenti versionati
make e2e              # CLI reale end-to-end
# oppure: python -m pytest
```

La stessa suite completa gira in CI (GitHub Actions) a ogni push e pull
request su Python 3.11 e 3.12, con report di coverage a branch.

## Licenza

MIT — vedi [LICENSE](LICENSE).
