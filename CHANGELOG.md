# Changelog

Tutte le modifiche rilevanti di audiolayers, nel formato
[Keep a Changelog](https://keepachangelog.com/it/1.1.0/). Il progetto
segue il versionamento semantico.

## [Unreleased]

### Added

- Ripetizioni casuali per voce nel pattern ritmico (issue #10): una voce
  può essere un dict `{value, repeat}` e si ripete un numero di volte
  estratto dall'RNG namespaced del layer (riproducibile col seed).
  `repeat` accetta un intero fisso (`3`), un range (`"2-4"`) o una lista
  di scelte (`[2, 7]`). I valori scalari restano ciclici semplici.

- Pool dinamico per-layer (issue #13): la cartella `pool` di un layer è
  ora derivabile. Nuova chiave `pool` nel blocco `provision` globale =
  cartella base condivisa dai layer senza `pool` (fabbisogni aggregati
  come da issue #8); `pool: auto` sul layer = sottocartella dinamica
  `<base>/<layer_id>`; senza nulla il default è `audio/pool/<layer_id>`;
  un path esplicito vince sempre (le partiture esistenti sono invariate).
  Il resolver condiviso `resolve_pool` vive in `audiolayers/audio/pool.py`
  ed è usato da provisioning e render; la voce `provision.pool` entra nel
  catalogo parametri per la GUI. Piano:
  `docs/plans/2026-07-06-004-pool-dinamico.md`.

### Changed

- La dipendenza `archivedigger` è pinnata al tag rilasciato `v0.1.0`
  invece del branch mobile `@main`: build riproducibili, gli aggiornamenti
  diventano un bump esplicito del tag.

- Il package `src` si chiama ora `audiolayers` e il motore è un pacchetto
  Python installabile (`pyproject.toml`, entry point console
  `audiolayers`): `pip install git+https://github.com/MU-prj/audiolayers@main`.
  La CLI diventa `python -m audiolayers.main` (o `audiolayers`);
  `requirements.txt` resta per il solo sviluppo (`-e .` + pytest).
  Piano e decisioni (D-S1..D-S7):
  `docs/plans/done/2026-07-05-003-engine-gui-split.md`.

### Removed

- La GUI web (`src/web/`, `make gui`, dipendenza flask) trasloca nel
  repository dedicato
  [MU-prj/audiolayers_gui](https://github.com/MU-prj/audiolayers_gui),
  che consuma il motore come pacchetto installato. I punti di contatto
  restano tre funzioni di libreria: `render_score`, `provision_score`,
  `catalog`.

### Added

- CI GitHub Actions (`.github/workflows/ci.yml`): l'intera suite
  (unit + integration + golden + e2e) gira a ogni push e pull request su
  Python 3.11 e 3.12, con report di coverage a branch. Copertura del motore
  di sintesi portata al 100% (riga e ramo); gli unici punti scoperti residui
  sono le guardie di entrypoint (`__main__`) e un ramo GUI latente.
- Test dello stadio di output del motore a livello integration
  (`tests/integration/test_output_stage.py`, `render_score` in-process):
  report del picco/CLIPPING, `--normalize`, risoluzione del formato
  (flag esplicito e alias `aif`) e bit depth/PCM_24 — finora esercitati solo
  dagli e2e via subprocess, quindi invisibili a coverage. Aggiunti anche gli
  e2e mancanti per il CLIPPING e i percorsi d'errore di validazione
  (envelope builder, parameter, catalogo, overflow) e del provisioning.
- Issue #8 — politiche di provisioning: `provision.mode`
  (per-fragment/threshold/fixed) con `files`/`variety`, margini
  automatici `min_margin` e `max_factor`; blocco `provision` anche a
  livello di partitura (digger globale, fabbisogni aggregati per pool).
  In GUI: controlli nella sezione digger e toggle «digger globale».

### Changed

- Griglia ritmica e durata del grano ora componibili: `fragment.rhythm`
  decide quando nasce un grano, `fragment.duration`(+range) quanto dura
  (staccato granulare). Niente più mutua esclusione.
- `distribution` estesa fino a 2: oltre 1 lo spread asincrono si
  amplifica (0..2×IOI×d), nuvole con grappoli e buchi marcati.
- GUI: parametri riordinati per criterio (tempo → grano → tessuto →
  sorgente → uscita), grano visibile anche in modalità ritmica,
  riquadro info incastonato in alto a destra (bianco), effetto rilievo
  3D sui pannelli layer, editor curve: click secco rimuove il punto,
  tasto destro apre l'editor manuale di ascissa/ordinata (fix anche al
  bug dei punti che si scambiavano durante il drag).

### Changed

- Deepening architetturale (fonte unica dei parametri): nuovo catalogo
  `src/parameters/catalog.py` esposto come `/api/params` — la GUI genera
  i controlli dal motore, le tabelle JavaScript duplicate sono sparite
  (bounds/enum/default non possono più divergere).
- Seam `pool` esplicito (`src/audio/pool.py`): scansione, estensioni e
  idoneità in un modulo solo; convenzione solo/mute pubblica in
  `core.layer_plan.active_layers`. Il provisioning non importa più
  privati del renderer; via `LocalPoolSource` (seam finto mai usato).
- `fragment.duration` assemblata in un punto solo (DurationStrategy):
  eliminata la copia morta nello schema dichiarativo.

### Fixed

- I bounds dichiarati ora sono applicati davvero: `master_volume`
  validato al parse (prima si poteva scrivere 999 senza errori),
  `fragment.attack`/`release` entrano nel registry con bounds 0–0.5 s.

### Added

- GUI web minimale (`make gui` / `python -m src.web`, Flask + vanilla JS):
  controlli on/off per ogni parametro (off = default del motore), slider,
  mini editor breakpoint per gli envelope, render come job asincrono con
  player integrato e download, provisioning `--dig` con un toggle,
  export/import YAML round-trip con la CLI. Stile bianco minimale.
- GUI v2 a tre finestre: pannello **inviluppi** a sinistra (le curve si
  editano lì come corsie nominate, il pannello principale resta pulito;
  apri/chiudi, larghezza regolabile) e pannello **daw** a destra col
  render: forma d'onda ↔ spettrogramma (FFT propria, scala log, b/n),
  righello temporale, playhead sincronizzato, click per seek, trasporto.
  La colonna centrale resta sempre centrata.
- GUI: terminale a tendina (output reale del motore via /api/log),
  tema chiaro/scuro ☀/☾ persistito, valori scrivibili a mano accanto
  agli slider, layout compatto web 1.0 × apple.
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
