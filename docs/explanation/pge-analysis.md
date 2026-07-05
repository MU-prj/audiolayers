---
slug: pge-analysis
type: explanation
status: stable
created: 2026-07-02
tags: [pge, architettura, roadmap, tendency-masks, envelope, voices]
sources:
  - https://github.com/DMGiulioRomano/PythonGranularEngine
---

# PythonGranularEngine — analisi e roadmap di iniezione

Analisi del repository [PythonGranularEngine](https://github.com/DMGiulioRomano/PythonGranularEngine)
(PGE) condotta il 2026-07-02 durante il design di audiolayers, su clone del
sorgente completo. PGE è un ambiente compositivo per sintesi granulare
(YAML → Csound SCO / NumPy → AIF), ispirato al DMX-1000 di Barry Truax;
audiolayers opera alla scala dei *frammenti di file* invece che dei grani,
ma i due sistemi condividono il modello dichiarativo. Questo documento
cataloga **tutto ciò che vale la pena iniettare**, con il dettaglio di come
PGE lo implementa e le note di adattamento.

Mappa concettuale: `stream → layer` · `grain → fragment` ·
`pointer.start → punto di lettura` · `grain.duration → apertura`.

---

## 1. Già iniettato nella v1 (per riferimento)

| Ingrediente PGE | File PGE | Dove vive in audiolayers |
|---|---|---|
| Sistema parametri a 3 livelli (bounds / schema / parser) | `parameters/parameter_definitions.py`, `parameter_schema.py`, `parser.py` | `audiolayers/parameters/` (D18) |
| Default automatici per chiavi YAML assenti (`ParameterSpec.default` + `_get_nested`) | `parameter_factory.py` | `audiolayers/parameters/parser.py` |
| Tendency mask `base ± range`, convenzione suffisso `_range` | `parameter.py` | `audiolayers/parameters/parameter.py` (D5) |
| `fill_factor` (= nostro F) e `distribution` (= nostro α, blend sync↔async Truax) | `controllers/density_controller.py` | `audiolayers/core/fragment_sequence.py` (D2, D3) |
| Envelope breakpoints + `time_mode absolute/normalized` | `envelopes/envelope.py` | `audiolayers/envelopes/` (M2) |
| Seeding namespaced sha256 (modello delle voci PGE, esteso a tutto) | `shared/seeding.py` | `audiolayers/shared/seeding.py` (D14) |
| `solo`/`mute` (i solo vincono, poi i mute) | `engine/generator.py` `_filter_solo_mute` | `audiolayers/engine/render.py` (D15) |
| Bounds con validazione severa al parse, errori parlanti | `parser.py` `_validate_and_clip` | `audiolayers/parameters/parser.py` |
| Convenzione esclusività **a errore esplicito** (non priorità silenziosa) | blocco pitch post-refactor | `duration` vs `rhythm` in `duration_strategy.py` |
| Docs Diátaxis, `plans/done/`, frontmatter con `sources` | `docs/` | `docs/` |

---

## 2. Da iniettare — il catalogo dettagliato

### 2.1 Envelope avanzati ⭐ (il singolo upgrade più ricco)

Il sistema envelope di PGE (`envelopes/`) è molto oltre il nostro lineare:

**a) Interpolazione `cubic` (Fritsch-Carlson).** Hermite cubica con tangenti
calcolate dall'algoritmo Fritsch-Carlson: **monotonia garantita**, nessun
overshoot tra breakpoint adiacenti; nei punti critici (cambio di pendenza)
la tangente è forzata a zero. Caso speciale a 2 punti: tangenti agli estremi
a zero → smoothstep simmetrico `v(s) = v0 + (v1−v0)(3s² − 2s³)`, così
`cubic` su due punti produce sempre una S, mai una retta camuffata.
L'integrale è Simpson composito (10 sotto-intervalli per segmento).

**b) Interpolazione `step`** (hold-left): cambi discontinui di sezione,
automazioni "a quantità fisse". Integrale = area di rettangolo.

**c) Tipo di interpolazione per-punto** (issue #54 di PGE): ogni breakpoint
può dichiarare la strategia del *segmento che parte da lui*:
`[[0, 5, 'cubic'], [0.5, 30, 'step'], [1, 5]]` o la forma dict
`{t, v, type}`. Ultimo punto: `type` ignorato con warning. Le tangenti
Fritsch-Carlson si calcolano sull'intera lista e si applicano solo ai
segmenti cubic (coerenza ai confini tra strategie).

**d) Formato compatto (cicli ripetuti)** — `envelope_builder.py`:

```
[pattern_points, end_time, n_reps, interp?, time_dist?, wrap?]
```

- `pattern_points`: pattern in **percentuale del ciclo** `[[x%, y], …]`;
- `end_time` è il **tempo assoluto finale**, non la durata (in formato misto
  la durata effettiva è `end_time − offset` dall'ultimo breakpoint scritto);
- `x_finale < 100` → hold (gap costante tra cicli); `wrap=true` → il gap
  interpola verso il primo `y` del ciclo (loop chiuso, breakpoint sintetico
  a `cycle_end − ε`);
- `DISCONTINUITY_OFFSET = 1e-6` s inserito tra cicli per discontinuità
  intenzionali senza degenerare l'interpolazione.

**e) `TimeDistributionStrategy`** (`time_distribution.py`): come distribuire
le durate dei cicli del formato compatto — `linear` (uniformi),
`exponential` (accelerando), `logarithmic` (ritardando),
`{type: geometric, ratio: r}`, `{type: power, exponent: e}`. Vincolo:
`sum(durations) == total_time`. Musicalmente: pulsazioni che accelerano
dentro un singolo parametro.

**f) Formato misto**: breakpoint espliciti e blocchi compatti nella stessa
lista, con offset temporale automatico.

**g) `integrate(a, b)` analitico per segmento** — in PGE serve al calcolo
del numero di grani su density envelope. Per noi: utile il giorno in cui
`fill_factor` envelope dovrà produrre conteggi esatti o visualizzazioni.

*Adattamento*: (a)+(b)+(c) entrano nel nostro `envelope_interpolation` come
Strategy (l'ABC c'è già); (d)+(e)+(f) sono un modulo builder a parte che
espande a breakpoint piatti — la nostra `Envelope` non cambia.

### 2.2 Espressioni matematiche nei valori

`generator.py::_eval_math_expressions` valuta stringhe tra parentesi via
`safe_eval`: `onset: (pi)`, `duration: (10/2)`, `pan: (360/12)`. Comodità
compositiva pura, costo minimo. *Adattamento*: pre-processing del dict YAML
prima del parsing parametri, whitelist di nomi (`pi`, `e`, operatori).

### 2.3 Dephase — probabilità di variazione (ProbabilityGate)

In PGE la tendency mask ha un **secondo asse**: non solo *quanto* variare
(`_range`) ma **con che probabilità applicare la variazione** per-grano.

- `ProbabilityGate` (Gateway pattern, `shared/probability_gate.py`):
  `NeverGate`, `AlwaysGate`, `RandomGate(p)`, `EnvelopeGate(env)` — la
  probabilità può essere una curva nel tempo;
- YAML `dephase`: `false` (default: i `_range` espliciti sono sempre
  attivi), `null` (probabilità implicita 1%), scalare globale `50`,
  envelope globale, o **dict per-parametro**
  (`{volume: 30, pan: [[0,0],[30,80]]}`);
- semantica fine del dict: chiave assente/`null` = quel parametro applica il
  suo `_range` al 100% (dichiari solo ciò che vuoi *ridurre*);
- `default_jitter` nei bounds (`ParameterBounds.default_jitter`): quando il
  gate è attivo ma il parametro non ha `_range` esplicito, si applica un
  jitter implicito di entità predefinita (es. ±3 dB volume, ±30° pan);
  con `range` esplicito (anche 0) il jitter implicito NON si applica;
- `range_always_active: true` per forzare i range anche senza dephase.

*Valore per noi*: texture in cui solo il 20% dei frammenti devia — una
dimensione espressiva che `_range` da solo non dà. *Adattamento*: gate
iniettato nel nostro `Parameter` (slot già previsto dal design), con RNG
namespaced `f"{seed}:{layer_id}:gate:{param}"` — in PGE i gate usano il
`random` globale, noi no (vedi §4).

### 2.4 VariationStrategy oltre l'additiva

`strategies/variation_strategy.py` — la variazione entro banda è una
Strategy con 4 modi, selezionata dai bounds (`variation_mode`):

| Modo | Formula | Uso PGE | Uso potenziale audiolayers |
|---|---|---|---|
| `additive` | `distribution.sample(base, range)` | volume, pan, density | già nostro (unico) |
| `quantized` | `base + round(sample(0, range))` | pitch in semitoni | trasposizioni a griglia (§2.6), conteggi |
| `invert` | `1.0 − base` (comandata solo dal gate) | reverse | lettura reverse dei frammenti |
| `choice` | scelta da lista (o `all` → tutte le finestre) | finestra del grano | inviluppo del frammento da lista, **file dal pool per-frammento** |

E `DistributionStrategy` separata (uniform, gaussian): *come* si estrae
dentro la banda. Uniform ha semantica `center + uniform(−½,+½)·spread`
(spread totale, diversa dalla nostra ±range: attenzione in caso di port).

### 2.5 Sistema multi-voice ⭐ (la feature compositiva più grossa)

`voices` in PGE moltiplica uno stream in N voci coordinate
(`controllers/voice_manager.py`, `strategies/voice_*.py`):

- **`num_voices`**: scalare o envelope, bounds [1, 64]. Con valore
  **frazionario** la voce di confine riceve un gain pari alla parte
  decimale (`volume += 20·log10(frac)`): le voci **sfumano** dentro/fuori
  invece di accendersi di colpo. `max_voices = ceil(picco)` precomputato.
- **`scatter`** ∈ [0,1]: 0 = tutte le voci sincrone sullo stesso IOT,
  1 = ogni voce ha IOT indipendente, blend lineare. Cursori temporali
  per-voce che divergono con `scatter > 0` e `distribution > 0`.
- **Strategie per dimensione** (voce 0 = sempre riferimento, offset zero):
  - *pitch*: `step` (voce i → i·step), `range` (distribuzione lineare in
    [0, ampiezza]), `chord` (accordi nominali: maj/min/dim/aug/sus, 7e/9e/
    11e/13e, con `inversion`), `stochastic` (offset per-voce fisso seedato,
    magnitudine time-varying), `spectral` (voci sui parziali armonici:
    `round(12·log₂(i+1))` semitoni → 0, 12, 19, 24, 28, 31…);
  - *unit della distribuzione pitch*: la geometria è dell'unità —
    famiglia EDO additiva nel log (`2^(pos·amount/N)`), `ratio` geometrica
    (`amount^pos`, ottave pulite con `step: 2`);
  - *onset_offset*: `linear` (i·step), `geometric` (step·base^(i−1)),
    `stochastic` (in [0, max]);
  - *pointer*: `linear`/`stochastic`, flag `normalized: true` per offset in
    frazione del buffer invece che secondi (fix dell'ambiguità di unità,
    issue #80 PGE);
  - *pan*: `range` (equidistanti in ±spread/2), `stochastic`, `step`.
- **Seeding per-voce**: `sha256(f"{seed}:{stream_id}:{voice_index}")` — il
  modello che abbiamo generalizzato.

*Valore per noi*: un layer che diventa coro — la stessa sequenza di
frammenti sdoppiata su N voci con offset coordinati di tempo/lettura/pan
(e trasposizione, se/quando la introduciamo). È il moltiplicatore di
densità compositiva di *Riverrun*. *Adattamento*: `voices` come blocco di
layer; le strategy per dimensione sono già nel nostro stile (D17); il fade
frazionario di `num_voices` è raffinato e vale il port fedele.

### 2.6 Trasposizione unit-driven (il grande assente in audiolayers)

audiolayers oggi **non altera il pitch**. PGE ha un modello maturo
(`parameters/pitch_unit.py`, `controllers/pitch_controller.py`):

- una sola chiave-unità per blocco: `semitones` (12-EDO), `quarter_tone`
  (24), `eighth_tone` (48), `cents` (1200), `edo: N` + `value` (griglia
  arbitraria, es. 31-EDO), `ratio` (moltiplicatore diretto, [0.001, 8]);
- conversione EDO → ratio: `2^(valore/N)`; bounds derivati dall'unità
  (±3 ottave EDO), non dal registry — `PitchUnit` è l'unica fonte di
  verità (bounds_override nel parser);
- più chiavi-unità insieme → errore con hint (niente priorità implicite);
  chiavi sconosciute nel blocco → errore (i refusi non passano in silenzio);
- `range` quantizzato sulla griglia dell'unità; **detune implicito** sotto
  dephase senza `range`: ±12 cents continui applicati in ratio-space *dopo*
  la quantizzazione (micro-disallineamento naturale).

*Adattamento*: per frammenti lunghi la trasposizione = resampling del
segmento (`soxr` con ratio variabile) → cambia anche la durata effettiva
(varispeed, musicalmente onesto alla nostra scala) oppure time-stretch
(fuori scope v1). Il blocco YAML e `PitchUnit` si portano quasi identici.

### 2.7 Pointer avanzato: speed_ratio e finestre di loop

- **`speed_ratio`** ∈ [−100, 100], envelope-abile: velocità e *direzione*
  di lettura (negativo = indietro). In PGE guida anche il reverse "auto"
  del grano. Per noi: frammenti letti al contrario o a velocità variabile.
- **Finestre di loop**: `loop_start` + (`loop_end` xor `loop_dur`,
  `loop_end` vincolato a [0, durata_file], `loop_dur` può **scavalcare la
  fine del file** — la finestra prosegue dall'inizio); tutti envelope-abili
  → *finestra di loop mobile* che scorre sul file. `loop_unit: normalized`
  scala i **valori** su [0, durata_file].
- **Confinamento modulare**: con loop attivo, la posizione finale di ogni
  grano (base + offset stocastico + offset di voce) è confinata dentro la
  finestra via wrap modulare — si legge solo da lì; è confinato il *punto
  di lettura*, non la coda del grano. `offset_range` è scalato
  sull'ampiezza della finestra attiva.
- Validazione: `loop_end <= loop_start` statico → errore; con envelope
  l'ordine non è validato (può legittimamente variare nel tempo).

*Valore per noi*: il loop mobile è una lente che scorre sul file sorgente —
poetica molto vicina al nostro `pointer.start` envelope, ma con larghezza
di banda controllabile. Si integra come estensione del blocco `pointer` +
una `OverflowStrategy` consapevole della finestra.

### 2.8 Inviluppi del frammento: registro finestre, transizioni, multi-stato

Il nostro `fragment.envelope` ha 2 voci (raised_cosine, rectangle). PGE
(`window_registry.py`, `window_selection_strategy.py`) ne ha **16** in tre
famiglie — window (hanning, hamming, bartlett, blackman, blackman_harris,
gaussian, kaiser, rectangle, sinc), custom (half_sine), asimmetriche
(expodec, expodec_strong, exporise, rexpodec, rexporise…) — più tre
modalità di selezione:

```yaml
envelope: [hanning, expodec, gaussian]     # choice casuale per grano
envelope: {from: hanning, to: bartlett, curve: [[0,0],[30,1]]}  # morphing
envelope: {states: [[0.0, hanning], [0.3, bartlett], [1.0, gaussian]],
           curve: [[0,0],[30,1]]}          # percorso multi-stato
```

Il morphing è probabilistico (la curva è la probabilità di pescare `to`);
`all` espande a tutte le finestre. Le asimmetriche (expodec = attacco netto
e coda esponenziale, alla Roads) sono *molto* caratterizzanti alla nostra
scala temporale. *Adattamento*: registry di finestre + `choice`/transizione
come `FragmentEnvelopeStrategy` aggiuntive.

### 2.9 Reverse

Sintassi PGE deliberata: `reverse:` (chiave presente e vuota) = reverse
forzato; chiave assente = auto (segue il segno di `speed_ratio`);
`reverse: true/false` = **errore** (evita l'ambiguità del bool YAML).
Variation `invert` + `dephase.reverse: 5` = 5% dei frammenti al contrario.

### 2.10 Clip strategies (gestione code ai confini)

`GrainClipStrategy` — post-filtro sui grani, unica fonte di verità su quali
esistono (`stream.voices`): `overflow_margin` (grano valido se sta dentro
`stream_end + clip_margin`) e `passthrough` (nessun filtro, il buffer si
estende). La nostra D7 ("mai mozzare, sfora pure") equivale a un
`passthrough` sempre attivo; se un giorno servisse un layer a durata
rigida, questa è la policy pronta — come Strategy, non come cambio di
semantica globale.

### 2.11 Caching incrementale per-stream

`rendering/stream_cache_manager.py` + `docs/explanation/caching.md`:

- fingerprint SHA-256 del dict YAML dello stream (escluse chiavi non-audio
  `solo`/`mute` — issue #108: il toggle non deve sporcare lo stem);
- manifest JSON `cache/{yaml}.json` (`{stream_id: fingerprint}`),
  ispezionabile e diff-friendly;
- `is_dirty` = id assente ∨ fingerprint cambiato ∨ file output assente;
- garbage collection implicita a ogni build (manifest + file orfani);
- **trappola documentata**: il fingerprint non copre il *contenuto* dei
  file sorgente — se cambi il wav ma non il YAML, lo stream resta clean.

*Per noi*: rilevante quando i render diventeranno lunghi (pool grandi,
molti layer). Nota importante: col nostro seeding namespaced la cache è
**coerente per costruzione** (i grani di un layer non dipendono da quali
altri layer sono dirty) — in PGE questa coerenza manca finché non risolvono
PGE#154. Miglioria facile alla trappola: includere nel fingerprint
`(path, mtime, size)` dei file del pool.

### 2.12 Export e visualizzazione

- **Score visualizer** (`rendering/score_visualizer.py`): partitura
  grafica PNG del piano dei grani (tempo × pitch/pointer, opacità = volume
  — la voce in fade frazionario appare trasparente). Per audiolayers:
  timeline frammenti per layer (tempo × pan o × file sorgente) — feedback
  visivo prima dell'ascolto, prezioso in composizione.
- **Render modes**: `mix` (file unico) vs `stems` (un file per stream) —
  per noi: stems per layer, banale col mix attuale e utilissimo in DAW.
- **Reaper project writer** (`reaper_project_writer.py`): genera `.rpp`
  con gli stems già disposti (riuso tab, autokill — vedi plans/done).
- **Sonic Visualiser exporter** e **grain JSON writer**: piani annotati e
  dump strutturato dei grani per analisi esterne.

### 2.13 Errori e validazione

- Gerarchia con **hint** operativi (`shared/exceptions.py`:
  `MissingFieldError`, `InvalidFieldValueError`, `ParameterBoundError` con
  lista violazioni per-breakpoint, `InvalidStrategyConfigError`,
  `StrategyNotFoundError`) e `stream_id` attaccato all'errore;
- `validation_mode: strict | permissive` (config): strict solleva,
  permissive clippa e logga con messaggio dettagliato (valore, bound
  violato, deviazione). Noi siamo strict-only: la modalità permissive è
  una scelta compositiva legittima ("suona comunque, dimmi cosa hai
  toccato") da offrire prima o poi;
- il logger dedicato traccia le trasformazioni degli envelope compatti
  (input → cicli → breakpoint finali): debugging compositivo.

### 2.14 Processo e documentazione (meta, ma decisivo)

- **Diátaxis** rigoroso con frontmatter ricco: `sources:` (i file di cui il
  doc è specchio) e `last_synced_commit:` — la doc dichiara quando è stata
  allineata l'ultima volta;
- **how-to operativi** per ogni punto di estensione (`add-parameter`,
  `add-voice-strategy`, `add-window-function`, `add-renderer`,
  `add-error-class`, `make-parameter-envelope-aware`): 5 passi, file
  toccati, test da aggiornare — da replicare per i nostri punti di
  estensione (add-selection-strategy, add-overflow-strategy, …);
- `plans/` con naming `YYYY-MM-DD-NNN-tipo-nome-plan.md` e `done/`;
- CLAUDE.md di repo con: impact analysis obbligatoria prima di toccare
  moduli esistenti, regola di **impatto cross-repo** (modifiche alla
  superficie pubblica → analisi sui repo a valle + issue), TDD gate.

---

## 3. Anti-pattern osservati (da NON importare)

1. **`random.seed` globale** (`generator.py:113`): tutti i draw dei grani
   in un'unica sequenza condivisa → solo/mute e stato della cache alterano
   i render con seed fissato; refactor shiftano tutto. Documentato e
   proposto il fix in [PGE#154](https://github.com/DMGiulioRomano/PythonGranularEngine/issues/154).
   In audiolayers: namespaced ovunque dal giorno zero (D14).
2. **Codice morto in `parameter.py`**: `_strategy_additive/_quantized/
   _invert` sopravvissuti al refactor verso `VariationFactory`, con
   docstring di modulo che descrive ancora il design rimosso (stessa
   issue #154, sezione 2). Lezione: quando una Strategy sostituisce metodi
   interni, cancellarli nello stesso commit.
3. **Doppio stile di import** (`from parameters...` con `src` nel path):
   fonte di doppi-import; noi usiamo un solo stile `from audiolayers....`.
4. **Uniform con semantica spread-totale** ma documentata come ±range:
   ambiguità di contratto; da noi `range` è la semiampiezza, punto.

---

## 4. Priorità di iniezione suggerite

Ordinate per rapporto valore compositivo / costo:

| # | Cosa | Perché prima |
|---|---|---|
| 1 | **Envelope cubic/step + per-punto** (§2.1 a-c) | tocca ogni parametro esistente; ABC già pronta |
| 2 | **Dephase/ProbabilityGate + default_jitter** (§2.3) | secondo asse delle tendency mask; slot già nel design del Parameter |
| 3 | **Registro finestre + choice/transizioni** (§2.8) | timbrica dei frammenti, costo basso |
| 4 | **Formato compatto + TimeDistribution** (§2.1 d-f) | pattern ritmici dentro qualunque parametro |
| 5 | **Multi-voice** (§2.5) | la feature più grossa; richiede 1–4 mature |
| 6 | **speed_ratio + reverse** (§2.7, §2.9) | varispeed alla nostra scala; prepara il pitch |
| 7 | **Trasposizione unit-driven** (§2.6) | grande assente; dipende da 6 |
| 8 | **Loop windows con confinamento** (§2.7) | lente mobile sul file sorgente |
| 9 | **Stems per layer + score visualizer** (§2.12) | workflow DAW e feedback visivo |
| 10 | **Caching incrementale** (§2.11) | quando i render superano il minuto |

Espressioni matematiche (§2.2), clip strategies (§2.10), validazione
permissive e logging trasformazioni (§2.13), how-to (§2.14) si infilano
opportunisticamente dove capita il cantiere giusto.
