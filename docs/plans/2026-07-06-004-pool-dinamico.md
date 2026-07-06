# Plan 004 — Pool dinamico per-layer dal provision globale

Data: 2026-07-06 · Branch: `claude/skills-repo-setup-issues-4isyqz`
Issue: [#13](https://github.com/MU-prj/audiolayers/issues/13) (core) ·
[audiolayers_gui#3](https://github.com/MU-prj/audiolayers_gui/issues/3) (GUI)

## Obiettivo

Rendere la cartella `pool` di ogni layer derivabile automaticamente invece
di doverla scrivere a mano su ogni layer: nuova keyword `pool` nel blocco
`provision` globale come cartella base, sentinella `pool: auto` sul layer
per la sottocartella dinamica, default derivato `audio/pool/<layer_id>`
quando non c'è nulla.

## Semantica (tabella dei casi)

| `provision.pool` globale | `pool` del layer | cartella risolta |
|---|---|---|
| sì | assente | `<globale>` — condivisa (aggregazione issue #8) |
| sì | `auto` | `<globale>/<layer_id>` — opt-out dinamico |
| sì | `<path>` | `<path>` — opt-out esplicito |
| no | assente | `audio/pool/<layer_id>` |
| no | `auto` | `audio/pool/<layer_id>` (equivale ad assente) |
| no | `<path>` | `<path>` |

«Globale» = chiave `pool` presente (e non vuota) nel blocco `provision`
di radice; un blocco `provision` globale senza `pool` NON attiva la
condivisione: i layer senza `pool` cadono sul default derivato.

## Analisi (stato attuale)

`layer["pool"]` è letto direttamente in 3 punti:

| Punto | Chiamata | Effetto oggi |
|---|---|---|
| `provisioning/pool_source.py:54` | `ensure()` | KeyError se assente |
| `provisioning/pool_source.py:135` | raggruppamento globale | idem |
| `engine/render.py:147` | `scan_pool` | idem |

Il render e il provisioning devono vedere lo STESSO path: la derivazione
va in un punto comune. `audio/pool.py` è già il confine dichiarato tra i
due sottosistemi («Unico punto che sa cos'è un pool valido»): il resolver
vive lì.

## Decisioni

- **D-PD1** — `resolve_pool(layer, score=None) -> Path` in
  `audiolayers/audio/pool.py`; costanti `DEFAULT_POOL_BASE = "audio/pool"`
  e sentinella `"auto"`. Tutti e 3 i punti lo chiamano al posto
  dell'accesso diretto.
- **D-PD2** — `ensure(layer, seed)` (ramo per-layer, senza blocco globale)
  risolve con `score=None`: nel ramo per-layer non esiste `provision.pool`
  globale per costruzione, la firma pubblica non cambia.
- **D-PD3** — `_split_policy` estrae `pool` esplicitamente dal blocco
  provision: non è policy e non deve finire nella Config di archivedigger
  (campi sconosciuti = errore).
- **D-PD4** — Aggregazione issue #8 preservata: i layer senza override
  cadono nello stesso path risolto → stesso gruppo → fabbisogni sommati.
  `auto` e path espliciti diventano gruppi separati.
- **D-PD5** — Retrocompatibilità: le partiture esistenti
  (`scores/venti-strati.yaml`) hanno `pool:` esplicito su ogni layer →
  caso override → bit-identiche (lo verificano i golden).
- **D-PD6** — Catalogo: voce `provision.pool` (kind `text`, default `""`)
  per GUI e validazione; vuoto = nessuna base globale.
- **D-PD7** — GUI (`audiolayers_gui#3`): campo `pool` del layer a 3 stati
  (vuoto = derivato, `auto`, path esplicito); lo YAML emette `pool` SOLO
  per `auto`/esplicito. `score_builder` e `app.js` smettono di forzare
  `audio/pool/`. Select `default | auto | personalizzato` con preview del
  path risolto (stessa logica del resolver, lato JS).

## Passi (TDD, una slice verticale per ciclo)

### Core (`audiolayers`)

1. Resolver, RED→GREEN un caso alla volta (unit `tests/unit/test_pool.py`):
   esplicito senza globale → assente senza globale → assente con globale →
   `auto` con globale → esplicito con globale → `auto` senza globale.
2. Provisioning (unit/integration su `pool_source`):
   - `provision_score` con `provision.pool` globale e layer senza `pool` →
     download nella base condivisa, un solo gruppo/una query; `pool` non
     sporca la Config archivedigger (D-PD3);
   - layer con `pool: auto` nel globale → gruppo separato in
     `<base>/<layer_id>`;
   - `ensure` per-layer senza `pool` → `audio/pool/<layer_id>`.
3. Render: partitura con layer senza `pool` e file già in
   `audio/pool/<layer_id>` → renderizza (integration).
4. Catalogo: voce `provision.pool` presente e ben formata (unit).
5. Changelog (Added), plan → `docs/plans/done/`, suite completa, push,
   draft PR.

### GUI (`audiolayers_gui`)

6. `score_builder` RED→GREEN: `pool` vuoto non emesso → `auto` emesso →
   esplicito emesso → `parse_score` senza `pool` → `""` (niente default
   forzato) → round-trip stabile.
7. `app.js`: `newLayer` con `pool: ""`; select a 3 stati con input path
   condizionale e preview risolta; `doImport` senza rimpiazzi;
   `provision.pool` esclusa dal digger per-layer (ha senso solo globale).
8. Suite completa, push, draft PR (nota: mergiare DOPO la PR core — la
   voce di catalogo arriva dal motore).

## Fuori scope

- Validazione incrociata `auto`/globale in fase di parsing della
  partitura (il resolver è tollerante per costruzione).
- Migrazione delle partiture esistenti al nuovo default (restano valide).
