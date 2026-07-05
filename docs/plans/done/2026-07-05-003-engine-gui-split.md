# Plan 003 — Separazione motore / GUI: la GUI trasloca in audiolayers_gui

Data: 2026-07-05 · Branch: `claude/audiolayers-engine-gui-split-cygdcn`
Repo di destinazione GUI: `MU-prj/audiolayers_gui`

## Obiettivo

Estrarre la GUI web (`src/web/`) in un repository dedicato
(`audiolayers_gui`), lasciando in questo repo il solo motore di sintesi,
pubblicato come pacchetto Python installabile. La GUI diventa un
consumatore del motore come qualunque altro client (CLI inclusa).

## Analisi dell'accoppiamento (stato attuale)

L'accoppiamento è **unidirezionale**: la GUI importa il motore, il motore
non sa che la GUI esiste (nessun `import` da `src/web` nel resto di
`src/`). I punti di contatto sono esattamente tre funzioni:

| Seam | Chiamata | Dove |
|---|---|---|
| Render | `src.engine.render.render_score(score_path, wav_path)` | `web/app.py` (job runner) |
| Provisioning | `src.provisioning.pool_source.provision_score(path, client=…)` | `web/app.py` (toggle dig) |
| Catalogo parametri | `src.parameters.catalog.catalog()` | `web/app.py` (`/api/params`) |

Tutto il resto della GUI è autosufficiente: `jobs.py` (thread + polling),
`score_builder.py` (stato controlli ↔ dict partitura, pura manipolazione
dati), `static/` (HTML/JS/CSS vanilla). Il contratto largo è la
**partitura YAML**: la GUI costruisce un dict-partitura e lo passa al
motore via file; il catalogo `/api/params` resta la fonte unica dei
parametri (deepening D1), ora esposto dal pacchetto invece che da un
modulo interno.

Accoppiamenti residui nei test, da sciogliere nel trasloco:

- `tests/integration/test_web_api.py` importa `FakeArchiveClient` e
  `write_wav` da `tests/unit/test_pool_source.py` (helper del motore);
- lo stesso test legge `scores/stream-crescente.yaml` dal filesystem del
  repo motore.

## Decisioni

- **D-S1** Il motore diventa un pacchetto installabile. Il package
  `src` non è un nome pubblicabile: rinominato in `audiolayers`
  (`git mv src audiolayers` + aggiornamento import), con `pyproject.toml`
  (setuptools). La GUI lo installa con
  `pip install git+https://github.com/MU-prj/audiolayers@main`.
- **D-S2** La CLI resta nel motore: `python -m audiolayers.main`, più
  entry point console `audiolayers`. La suite (177 test) fa da rete di
  sicurezza per la rinomina, che precede la rimozione della GUI così da
  avvenire con la suite completa.
- **D-S3** Traslocano in `audiolayers_gui`: `web/app.py`, `web/jobs.py`,
  `web/score_builder.py`, `web/__main__.py`, `web/static/`, e i test
  `test_web_api.py`, `test_score_builder.py`, `test_job_manager.py`.
  Nel repo GUI il package si chiama `audiolayers_gui`
  (`python -m audiolayers_gui [--port]`); gli import del motore diventano
  `from audiolayers.engine.render import render_score`, ecc.
- **D-S4** Gli helper di test (`FakeArchiveClient`, `write_wav`) vengono
  **duplicati** in `audiolayers_gui/tests/helpers.py`: ~30 righe contro
  l'interfaccia stabile di `archivedigger`; un pacchetto di test
  condiviso non vale il costo. `stream-crescente.yaml` copiata come
  fixture in `tests/fixtures/` (l'originale resta nel motore, è materiale
  di partitura della CLI).
- **D-S5** `flask` esce da `requirements.txt` del motore (dipendenza solo
  GUI). Il repo GUI dichiara: `audiolayers @ git+…@main`, `flask`,
  `PyYAML`, `pytest`. Per lo sviluppo locale: `pip install -e ../audiolayers`.
- **D-S6** Ordine di merge: prima la PR del motore (rinomina + pacchetto +
  rimozione GUI), poi quella della GUI (che dipende dal motore su `main`).
- **D-S7** Il repo GUI mantiene le convenzioni di questo repo (Makefile
  con `make gui`/`make tests`, pytest.ini con `pythonpath = .`) ma nessun
  CHANGELOG: non ne ha uno e non se ne crea uno d'ufficio.

## Passi (commit atomici)

Repo motore:

1. questo plan;
2. rinomina package `src` → `audiolayers` (+ pytest.ini, Makefile, docs,
   scripts) — suite completa verde;
3. `pyproject.toml`: pacchetto `audiolayers` installabile, entry point
   CLI — suite verde;
4. rimozione `audiolayers/web/` + test web + target `make gui` + flask —
   suite ridotta verde;
5. docs (README, manuale, cli.md, INDEX) e CHANGELOG; plan → `done/`.

Repo GUI (TDD: prima i test, rossi, poi il codice):

1. scaffold (pytest.ini, Makefile, requirements, helpers, fixture);
2. test traslocati e adattati → **rossi** (modulo mancante);
3. codice GUI traslocato e adattato → **verdi**;
4. README e pulizia scaffold.

## Test

Nessun test nuovo di merito: il valore è che i 13 test web girino
identici nel repo GUI contro il motore **installato** (non più via
`pythonpath`), e che la suite del motore resti verde senza la GUI.
Rete di sicurezza per la rinomina: tutti i 177 test attuali.

## Fuori scope (idee per issue)

- Versionamento/release del motore su tag git (oggi la GUI punta a `main`).
- API HTTP del motore come servizio separato (oggi import in-process).
- Pubblicazione su PyPI.
