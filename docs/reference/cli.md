---
slug: cli
type: reference
status: stable
tags: [cli]
sources:
  - audiolayers/main.py
  - audiolayers/engine/render.py
  - audiolayers/provisioning/pool_source.py
---

# CLI Reference — audiolayers

```
python -m audiolayers.main SCORE.yaml -o OUT [opzioni]
```

| Opzione | Default | Significato |
|---|---|---|
| `SCORE.yaml` | richiesto | la partitura ([yaml.md](yaml.md)) |
| `-o, --output` | richiesto | file audio di output |
| `--format {wav,aiff,flac}` | dall'estensione di `-o`, altrimenti wav | formato contenitore; FLAC forza PCM 24 bit |
| `--bit-depth {32f,24}` | `32f` | float32 (immune al clipping su file) o PCM 24 bit |
| `--normalize` | off | porta il picco a −1 dBFS dopo il render (mai di default) |
| `--dig` | off | prima del render popola i pool mancanti da Internet Archive (archivedigger); vedi [yaml.md § provision](yaml.md#blocco-provision-opzionale-solo-con---dig) |

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
python -m audiolayers.main brano.yaml -o brano.wav

# FLAC per la condivisione, normalizzato
python -m audiolayers.main brano.yaml -o brano.flac --normalize

# WAV PCM 24 bit con seed forzato per un render riproducibile
python -m audiolayers.main brano.yaml -o brano.wav --bit-depth 24

# pipeline completa: analizza la partitura, scarica il pool, renderizza
python -m audiolayers.main scores/stream-crescente.yaml -o out/stream.wav --dig
```

## `--dig`: provisioning automatico del pool

Con `--dig` la CLI, prima del render e per ogni layer attivo:

1. costruisce la stessa sequenza di frammenti del render (stesso seed) e
   ne ricava i requisiti: *quanti* file servono (1 per frammento) e
   *quanto* devono durare (almeno il frammento più lungo, al massimo 10 s);
2. conta i file già idonei nel pool e scarica da Internet Archive solo la
   differenza (idempotente: rilanciare non riscarica nulla);
3. se l'archivio non copre il fabbisogno stampa `ATTENZIONE: ...` e il
   render procede comunque (la selezione cicla sui file disponibili).

La ricerca si orienta col blocco `provision` del layer ([yaml.md](yaml.md));
senza blocco valgono i default: licenza `cc`, solo formati lossless
(Flac/WAVE/AIFF — il loader non legge mp3).

Via Makefile: `make render SCORE=brano.yaml`.

## GUI web

La GUI web vive in un repository dedicato:
[MU-prj/audiolayers_gui](https://github.com/MU-prj/audiolayers_gui).
Consuma il motore come pacchetto installato (`pip install
git+https://github.com/MU-prj/audiolayers@main`) e si genera dal
catalogo dei parametri (`audiolayers.parameters.catalog`).
