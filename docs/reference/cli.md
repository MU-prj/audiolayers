---
slug: cli
type: reference
status: stable
tags: [cli]
sources:
  - src/main.py
  - src/engine/render.py
---

# CLI Reference — audiolayers

```
python -m src.main SCORE.yaml -o OUT [opzioni]
```

| Opzione | Default | Significato |
|---|---|---|
| `SCORE.yaml` | richiesto | la partitura ([yaml.md](yaml.md)) |
| `-o, --output` | richiesto | file audio di output |
| `--format {wav,aiff,flac}` | dall'estensione di `-o`, altrimenti wav | formato contenitore; FLAC forza PCM 24 bit |
| `--bit-depth {32f,24}` | `32f` | float32 (immune al clipping su file) o PCM 24 bit |
| `--normalize` | off | porta il picco a −1 dBFS dopo il render (mai di default) |

## Output diagnostico

- **Seed di sessione**: se la partitura non dichiara `seed`, ne viene
  generato uno dal timestamp e stampato con l'istruzione per riprodurre
  il render (`seed di sessione (generato): N -- aggiungi 'seed: N' ...`).
- **Report del picco**: sempre stampato a fine render.
  - `picco: -6.53 dBFS` — tutto bene;
  - `CLIPPING: picco +3.01 dBFS -- riduci master_volume di almeno 3.01 dB
    (o usa --normalize)` — il mix supera il fondo scala; con output float32
    il file resta integro, ma i player clipperanno.

## Esempi

```bash
# render standard (WAV float32 48 kHz)
python -m src.main brano.yaml -o brano.wav

# FLAC per la condivisione, normalizzato
python -m src.main brano.yaml -o brano.flac --normalize

# WAV PCM 24 bit con seed forzato per un render riproducibile
python -m src.main brano.yaml -o brano.wav --bit-depth 24
```

Via Makefile: `make render SCORE=brano.yaml`.
