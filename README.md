# audiolayers

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
python -m src.main brano.yaml -o brano.wav
```

Reference completa: [docs/reference/yaml.md](docs/reference/yaml.md) ·
[docs/reference/cli.md](docs/reference/cli.md)

## Stato

Motore v1 completo (M0–M10): multi-layer, tendency masks su tutti i
parametri, strategie di durata/selezione/overflow/inviluppo, mix con
master envelope e report del picco. Suite: 116 test (unit, integration,
golden, e2e). Le decisioni di design (D1–D20) sono nel
[plan di bootstrap](docs/plans/done/2026-07-02-001-project-bootstrap-plan.md).

## Setup

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows
# .venv/bin/pip install -r requirements.txt     # POSIX
```

## Test

```bash
make tests
# oppure: python -m pytest
```

## Licenza

MIT — vedi [LICENSE](LICENSE).
