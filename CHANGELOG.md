# Changelog

Tutte le modifiche rilevanti di audiolayers, nel formato
[Keep a Changelog](https://keepachangelog.com/it/1.1.0/). Il progetto
segue il versionamento semantico.

## [Unreleased]

### Added

- GUI web minimale (`make gui` / `python -m src.web`, Flask + vanilla JS):
  controlli on/off per ogni parametro (off = default del motore), slider,
  mini editor breakpoint per gli envelope, render come job asincrono con
  player integrato e download, provisioning `--dig` con un toggle,
  export/import YAML round-trip con la CLI. Stile bianco minimale.
- GUI: copertura completa delle modalità del motore — modalità ritmica
  (bpm envelope-abile + pattern) alternativa al grano continuo, solo/mute,
  time_mode, fill_factor_range, blocco digger per layer (licenza,
  collection, subject, query Lucene, formati) e pannello info fisso a
  destra: click sul nome di un parametro → spiegazione.

- Flag `--dig`: provisioning automatico del pool da Internet Archive via
  [archivedigger](https://github.com/MU-prj/archivedigger). Analizza la
  partitura (stessa sequenza di frammenti del render, stesso seed),
  ricava quanti file servono e le durate min/max richieste, scarica solo
  lo shortfall (idempotente) e poi renderizza. Blocco opzionale
  `provision` nel layer per orientare la ricerca; senza blocco default
  lossless + licenza `cc`.
- Partitura d'esempio `scores/stream-crescente.yaml`: stream singolo
  back-to-back con durate dei frammenti in envelope da 1 ms a 1 s su 60 s.
- Modulo condiviso `src/core/layer_plan.py`: render e analyzer assemblano
  la sequenza di frammenti nello stesso punto (niente divergenze).

## [1.0.0] — 2026-07-02

Bootstrap completo (M1–M10): motore dichiarativo YAML, tendency mask,
envelope, strategies (durata, selezione, overflow, inviluppo), pan
mid/side, mix multilayer con solo/mute, seeding namespaced riproducibile,
golden test e documentazione di riferimento.
