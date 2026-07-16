---
slug: manuale
type: tutorial
status: stable
created: 2026-07-03
tags: [manuale, tutorial, yaml, quickstart]
---

# Manuale di audiolayers

Questo è il manuale completo dello strumento: cosa fa, come si usa, come si
scrive una partitura. È pensato per essere letto dall'inizio alla fine la
prima volta, e poi consultato a salti. Per la specifica tecnica asciutta
vedi [reference/yaml.md](reference/yaml.md) e [reference/cli.md](reference/cli.md).

---

## Indice

1. [Che cos'è audiolayers](#1-che-cosè-audiolayers)
2. [Installazione e primo render](#2-installazione-e-primo-render)
3. [Il flusso di lavoro](#3-il-flusso-di-lavoro)
4. [I concetti fondamentali](#4-i-concetti-fondamentali)
5. [Come scrivere uno YAML](#5-come-scrivere-uno-yaml)
6. [La riga di comando](#6-la-riga-di-comando)
7. [Leggere gli errori](#7-leggere-gli-errori)
8. [Orientarsi nel repository](#8-orientarsi-nel-repository)
9. [I test](#9-i-test)
10. [Per approfondire](#10-per-approfondire)

---

## 1. Che cos'è audiolayers

audiolayers è un ambiente di composizione **dichiarativo**: tu descrivi in
un file di testo (la *partitura*, in formato YAML) che cosa vuoi ottenere,
e il programma genera un file audio. Non si suona in tempo reale: si
scrive, si renderizza, si ascolta, si corregge, si renderizza di nuovo.

L'idea musicale di base:

- hai una **collezione di file audio** (il *pool*): registrazioni,
  campioni, materiali di qualunque durata;
- il programma ne ritaglia dei **frammenti** — ogni frammento è una fetta
  di un file: *da che punto leggere*, *per quanto tempo*, *a che volume*,
  *dove nello spazio stereo*;
- i frammenti vengono **disposti lungo il tempo**, uno dietro l'altro,
  distanziati o sovrapposti, secondo le regole che dichiari;
- più sequenze indipendenti (i **layer**) si sommano nel mix finale.

Il controllo espressivo passa per due meccanismi che ritroverai ovunque:

1. **Tendency mask** (da Barry Truax): ogni parametro è un valore centrale
   più una banda di casualità — `base ± range`. Con range zero il
   parametro è esatto; con range ampio il parametro "respira" a caso
   dentro la banda.
2. **Envelope**: sia la base sia il range possono *cambiare nel tempo*,
   disegnati come spezzate di punti `[tempo, valore]`.

Tutto ciò che è casuale è governato da un **seed**: stesso seed → stesso
identico file audio, sempre. Nessuna sorpresa irriproducibile.

---

## 2. Installazione e primo render

Servono Python ≥ 3.12 e i pacchetti del progetto:

```bash
git clone https://github.com/domeniconasso/audiolayers
cd audiolayers
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      # Windows
# .venv/bin/pip install -r requirements.txt        # Linux/macOS/WSL
```

Verifica che tutto funzioni:

```bash
make tests        # oppure: python -m pytest
```

Primo render in tre mosse. Metti un paio di file audio (wav, aiff o flac)
in una cartella `audio/`, salva questo come `primo.yaml`:

```yaml
layers:
  - layer_id: "prova"
    duration: 10.0
    pool: "audio/"
    fragment:
      duration: 0.5
```

e lancia:

```bash
python -m audiolayers.main primo.yaml -o primo.wav
```

Otterrai 10 secondi di audio: frammenti da mezzo secondo, presi dai tuoi
file in ordine alfabetico, uno attaccato all'altro. Da qui in poi è tutto
un aggiungere chiavi alla partitura.

---

## 3. Il flusso di lavoro

Il ciclo tipico di una sessione:

```
scrivi/modifichi la partitura
        ↓
python -m audiolayers.main brano.yaml -o brano.wav
        ↓
leggi l'output diagnostico:
  · "seed di sessione (generato): N ..."  ← annotalo se il risultato ti piace!
  · "picco: -6.5 dBFS"                    ← ok
  · "CLIPPING: picco +2.1 dBFS ..."       ← abbassa master_volume
        ↓
ascolti → torni alla partitura
```

Due abitudini che ripagano:

- **Il seed è la tua memoria.** Se non dichiari `seed:` nella partitura,
  ne viene generato uno nuovo a ogni render (e stampato). Quando un
  render ti piace, copia il numero stampato dentro la partitura: da quel
  momento il brano è congelato e riproducibile per sempre.
- **Il picco è il tuo strumento di misura.** Il programma non abbassa mai
  il volume di nascosto: ti dice quanto sfori e di quanto ridurre. La
  correzione è tua, dichiarata nella partitura (`master_volume`).

---

## 4. I concetti fondamentali

### Layer

Un layer è una **voce indipendente** del brano: ha il suo pool, le sue
regole, il suo punto di inizio (`onset`) e la sua durata. I layer si
sommano nel mix stereo. Puoi ascoltarne uno solo (`solo: true`) o
zittirne uno (`mute: true`) senza toccare il resto — e grazie al seeding,
un layer in solo suona *esattamente* come suonerà nel mix.

### Frammento

L'unità minima: una fetta di un file del pool. Ogni frammento ha:

| Proprietà | Da dove viene |
|---|---|
| quale file | strategia di `selection` |
| quando parte | `fill_factor` + `distribution` |
| quanto dura ("apertura") | `fragment.duration` o `fragment.rhythm` |
| da che punto del file legge | `pointer.start` |
| volume | `volume` (dB) |
| posizione stereo | `pan` (gradi) |
| forma d'ampiezza | `fragment.envelope` (anti-click) |

### fill_factor — la spaziatura

Il parametro più importante. Governa la distanza tra gli attacchi:
**intervallo tra un attacco e il successivo = durata del frammento / F**.

```
F = 1    ▮▮▮▮▮▮▮▮   concatenazione perfetta: uno finisce, l'altro inizia
F = 0.5  ▮▮  ▮▮  ▮▮  silenzio tra i frammenti (più F scende, più vuoto)
F = 2    ▮▮▮▮        sovrapposizione (più F sale, più denso)
          ▮▮▮▮
```

Quando i frammenti si sovrappongono, i loro inviluppi producono
**dissolvenze incrociate automatiche**: non c'è un "crossfade" da
configurare, emerge da solo.

### distribution — dal metronomo alla nuvola

Con `distribution: 0` gli attacchi sono regolari come un metronomo. Con
`distribution: 1` ogni intervallo è estratto a caso (uniforme, tra 0 e il
doppio dell'intervallo regolare): una nuvola asincrona. I valori
intermedi sfumano tra i due mondi. È il modello di Truax.

### Tendency mask — base ± range

Quasi ogni parametro ha una sorella con suffisso `_range`:

```yaml
volume: -6.0        # la base
volume_range: 3.0   # la banda: ogni frammento pesca tra -9 e -3 dB
```

`range` assente o zero = valore esatto. E siccome base e range possono
essere envelope, la maschera può *aprirsi e chiudersi nel tempo*: un brano
che parte preciso e si sgretola progressivamente si scrive in due righe.

### Envelope — i valori che cambiano nel tempo

Ovunque sia accettato un numero, puoi scrivere una spezzata:

```yaml
fill_factor: [[0, 0.5], [60, 3.0]]
#             ↑tempo ↑valore
# a t=0 F vale 0.5; cresce linearmente; a t=60s vale 3.0
```

Prima del primo punto e dopo l'ultimo, il valore resta fermo (hold).
I tempi sono in secondi; con `time_mode: normalized` diventano frazioni
della durata del layer (0 = inizio, 1 = fine), utile per partiture che
devono scalare.

### Pan — lo spazio stereo circolare

Il pan è in gradi: `0` = centro, `+45` = tutto a sinistra, `−45` = tutto a
destra. Lo spazio è **circolare** (modulo 360): un envelope di pan che
cresce senza limiti — `[[0, 0], [60, 1440]]` — fa *ruotare* il suono
(quattro giri in un minuto). La potenza è costante a ogni angolo: girando
non cambia il volume percepito.

### Seed — la riproducibilità

Ogni sorgente di caso (maschere, selezione random, distribution) ha un
generatore **dedicato e nominato**, derivato da `seed + nome del layer +
nome del parametro`. Conseguenze pratiche: cambiare il `volume_range` di
un layer non altera le durate; mettere in solo un layer non ne cambia il
suono; stesso seed = stesso file, bit per bit.

---

## 5. Come scrivere uno YAML

Questa sezione parte da zero e costruisce una partitura completa, un
pezzo alla volta. Se non hai mai visto YAML, inizia da 5.1; altrimenti
salta a 5.2.

### 5.1 Le quattro regole del formato YAML

YAML è solo testo con indentazione. Ti servono quattro regole:

**1. Coppie chiave–valore, separate da due punti e uno spazio:**

```yaml
duration: 30.0
pool: "audio/"
```

Lo spazio dopo i due punti è obbligatorio. I numeri si scrivono nudi
(`30.0`, `-6`), i percorsi meglio tra virgolette (`"audio/"`).

**2. L'indentazione crea la gerarchia** (usa sempre 2 spazi, mai tab):

```yaml
fragment:            # blocco "fragment"
  duration: 0.5      # ...contiene la chiave "duration"
  attack: 0.008      # ...e la chiave "attack"
```

**3. Le liste si fanno con il trattino:**

```yaml
layers:              # "layers" è una lista
  - layer_id: "a"    # primo elemento (inizia col trattino)
    duration: 10.0   # ...le sue chiavi sono allineate sotto
  - layer_id: "b"    # secondo elemento
    duration: 20.0
```

Occhio all'allineamento: le chiavi di un elemento stanno alla stessa
colonna della prima chiave dopo il trattino.

**4. I commenti iniziano con `#`** e arrivano a fine riga. Usali tanto:
la partitura è anche il tuo diario di lavoro.

Due forme equivalenti che incontrerai: il blocco indentato e la forma
compatta tra graffe — `fragment: {duration: 0.5}` è identico al blocco
del punto 2. Usa quella che leggi meglio.

### 5.2 La partitura minima

```yaml
layers:
  - layer_id: "unico"      # un nome a tua scelta (identifica il layer)
    duration: 30.0          # quanto deve durare, in secondi
    pool: "audio/"          # cartella coi file sorgente
    fragment:
      duration: 0.5         # ogni frammento dura mezzo secondo
```

Cosa succede: il programma prende i file di `audio/` in ordine
alfabetico, ciclando; ritaglia frammenti da 0.5 s dall'inizio di ciascun
file; li mette in fila uno dietro l'altro (perché `fill_factor` non è
dichiarato e il suo default è 1); si ferma quando i 30 secondi sono
riempiti. **Regola d'oro dei default**: ogni chiave non scritta assume un
valore sensato — la tabella completa è in fondo (§5.9).

Nota su `duration`: è un *obiettivo*, non una tagliola. L'ultimo
frammento suona sempre per intero, quindi il file può durare qualche
frazione di secondo in più. Nessun frammento viene mai mozzato.

### 5.3 Aggiungere volume e spazio

```yaml
layers:
  - layer_id: "unico"
    duration: 30.0
    pool: "audio/"
    fragment:
      duration: 0.5
    volume: -6.0            # dB: 0 = com'è, -6 = metà ampiezza
    pan: 20.0               # gradi: positivo = sinistra
```

I dB in due parole: `0` lascia il suono com'è, `-6` lo dimezza, `-12` lo
riduce a un quarto, `+6` lo raddoppia (occhio al clipping). Il pan:
`0` centro, `+45` tutto a sinistra, `-45` tutto a destra.

### 5.4 Accendere il caso: le maschere

Aggiungi le sorelle `_range` ai parametri che vuoi rendere vivi:

```yaml
    fragment:
      duration: 0.5
      duration_range: 0.2   # durate tra 0.3 e 0.7 s
    volume: -6.0
    volume_range: 3.0       # volumi tra -9 e -3 dB
    pan: 0.0
    pan_range: 30.0         # posizioni tra -30° e +30°
```

Ogni frammento pesca il suo valore dentro la banda. Il risultato è
riproducibile: aggiungi `seed: 42` in cima al file (fuori da `layers`,
senza indentazione) e ogni render sarà identico al precedente.

### 5.5 Spaziatura e ritmo del tessuto

```yaml
    fill_factor: 0.7        # un po' di aria tra i frammenti
    distribution: 0.5       # a metà tra metronomo e nuvola
```

Prova questi tre caratteri estremi per farti l'orecchio:

| Carattere | fill_factor | distribution |
|---|---|---|
| Scansione regolare, ipnotica | `1.0` | `0.0` |
| Gocce rade e imprevedibili | `0.3` | `1.0` |
| Massa densa e brulicante | `3.0` | `1.0` |

### 5.6 Far evolvere i parametri: gli envelope

Sostituisci un numero con una lista di punti `[tempo, valore]`:

```yaml
    fill_factor: [[0, 0.3], [30, 3.0]]     # da rado a densissimo in 30 s
    distribution: [[0, 0.0], [30, 1.0]]    # da metronomo a nuvola
    pan: [[0, 0], [30, 720]]               # due giri completi di rotazione
    volume_range: [[0, 0], [30, 6]]        # la maschera si apre pian piano
```

Ogni riga è una drammaturgia in miniatura. Si possono combinare
liberamente: base fissa con range a envelope, base a envelope con range
fisso, entrambi a envelope.

Se preferisci ragionare in proporzioni invece che in secondi, dichiara
`time_mode: normalized` a livello di layer e scrivi i tempi tra 0 e 1:

```yaml
    time_mode: normalized
    fill_factor: [[0, 0.3], [0.5, 3.0], [1, 0.3]]   # picco a metà brano
```

### 5.7 Il punto di lettura e le durate ritmiche

**Da dove leggere dentro i file** — `pointer.start` va da 0 (inizio del
file) a 1 (fine):

```yaml
    pointer:
      start: [[0, 0.0], [30, 1.0]]   # scorre tutto il file lungo il brano
      start_range: 0.1               # ± un po' di dispersione
      overflow: loop                 # se la fetta sfora la fine del file:
                                     #   clamp_back = arretra (default)
                                     #   loop       = riparte dall'inizio
                                     #   zero_pad   = completa con silenzio
```

**Durate ritmiche invece che a maschera** — in alternativa a
`duration`/`duration_range` (mai insieme: è un errore), un pattern
ciclico su un tempo metronomico:

```yaml
    fragment:
      rhythm:
        bpm: 120
        pattern: [0.25, 0.125, 0.125, 0.5]
        # frazioni di semibreve: 0.25 = semiminima (un movimento),
        # a 120 BPM → 0.5 s; il pattern si ripete ciclicamente
```

Con `fill_factor: 1` e un pattern ritmico ottieni attacchi su griglia:
è il modo di scrivere ritmi veri. Il `bpm` accetta envelope
(accelerando/ritardando).

**Ripetizioni casuali per voce** — una voce del pattern può essere un
dict `{value, repeat}`: a ogni giro il valore si ripete un numero di
volte estratto dall'RNG del layer (riproducibile col seed). `repeat`
accetta tre forme:

```yaml
    fragment:
      rhythm:
        bpm: 120
        pattern:
          - 0.5
          - {value: 0.125, repeat: 3}        # fisso: sempre 3 volte
          - {value: 0.125, repeat: "2-4"}    # range: da 2 a 4 volte
          - {value: 0.25,  repeat: [2, 7]}   # scelte: solo 2 o 7 volte
```

I valori scalari restano ciclici semplici (retrocompatibile).

**Come vengono scelti i file** — blocco `selection`:

```yaml
    selection:
      strategy: random     # sequential (default) | rotation | random
```

`sequential` = in ordine, ciclando; `rotation` = come uno shuffle-play
(ogni file una volta per giro, mai due volte di fila lo stesso giro);
`random` = dadi puri.

### 5.8 Più layer, il master, il tocco finale

```yaml
sample_rate: 48000
seed: 424242
master_volume: [[0, 0], [90, -12]]    # il mix sfuma negli ultimi 30 s

layers:
  - layer_id: "tappeto"
    onset: 0.0                # parte subito
    duration: 90.0
    pool: "audio/paesaggi/"
    fill_factor: [[0, 0.6], [90, 2.0]]
    distribution: 0.3
    fragment: {duration: 1.2, duration_range: 0.4}
    pointer: {start: [[0, 0], [90, 1]], overflow: loop}
    volume: -12.0
    pan_range: 40.0

  - layer_id: "ritmo"
    onset: 30.0               # entra a 30 secondi
    duration: 45.0
    pool: "audio/percussioni/"
    selection: {strategy: rotation}
    fragment:
      rhythm: {bpm: [[0, 90], [45, 140]], pattern: [0.125, 0.0625, 0.0625]}
      attack: 0.003           # inviluppo più scattante per le percussioni
      release: 0.005
    volume: -6.0
    pan: [[0, -30], [45, 30]]
    # mute: true              # ← decommentando, questo layer tace
    # solo: true              # ← decommentando, suona SOLO questo
```

Note su questo esempio:

- `onset` posiziona il layer sulla timeline globale: il ritmo entra a 30″;
- `master_volume` agisce sul mix già sommato — è il punto giusto per i
  fade globali e per sistemare l'headroom quando il report segnala
  clipping;
- `attack`/`release` regolano l'inviluppo anti-click di ogni frammento
  (default: 8 e 10 millesimi di secondo — dolci; per materiali percussivi
  accorciali). Con `envelope: rectangle` lo togli del tutto (a tuo
  rischio di click);
- `solo`/`mute` sono gli interruttori di lavoro: si aggiungono e tolgono
  senza cambiare nient'altro del suono.

### 5.9 Tabella riassuntiva delle chiavi

Top-level (fuori da `layers`, senza indentazione):

| Chiave | Default | Cosa fa |
|---|---|---|
| `sample_rate` | `48000` | frequenza di campionamento del progetto |
| `seed` | generato+loggato | congela il caso: stesso seed = stesso render |
| `master_volume` | `0.0` | dB sul mix finale (scalare o envelope) |
| `layers` | — | la lista dei layer (obbligatoria) |

Per ogni layer:

| Chiave | Default | Cosa fa |
|---|---|---|
| `layer_id` | `"layer"` | nome (usalo sempre: governa anche il seed) |
| `onset` | `0.0` | quando entra sulla timeline (s) |
| `duration` | — | durata-obiettivo (s, obbligatoria) |
| `pool` | derivato | cartella sorgenti; assente → `audio/pool/<layer_id>` (o la base `provision.pool` globale); `auto` → `<base>/<layer_id>` |
| `solo` / `mute` | — | interruttori d'ascolto |
| `time_mode` | `absolute` | `normalized` = tempi envelope in [0,1] |
| `selection.strategy` | `sequential` | `rotation` \| `random` |
| `fill_factor` (+`_range`) | `1.0` | spaziatura: IOI = durata/F |
| `distribution` | `0.0` | 0 metronomo ↔ 1 nuvola |
| `fragment.duration` (+`_range`) | `0.5` | apertura del frammento (s) |
| `fragment.rhythm.bpm/pattern` | — | durate ritmiche (esclude `duration`) |
| `fragment.envelope` | `raised_cosine` | `rectangle` = nessun inviluppo |
| `fragment.attack` / `release` | `0.008` / `0.010` | fade anti-click (s) |
| `pointer.start` (+`_range`) | `0.0` | punto di lettura [0,1] |
| `pointer.overflow` | `clamp_back` | `loop` \| `zero_pad` |
| `volume` (+`_range`) | `0.0` | dB del frammento |
| `pan` (+`_range`) | `0.0` | gradi, +45 = sinistra, spazio circolare |

I limiti di validità di ogni parametro (oltre i quali la partitura si
ferma con errore chiaro) sono in [reference/yaml.md](reference/yaml.md#tabella-bounds).

---

## 6. La riga di comando

```bash
python -m audiolayers.main PARTITURA.yaml -o USCITA [opzioni]
```

| Opzione | Effetto |
|---|---|
| `-o out.wav` | file di uscita (obbligatorio) |
| `--format wav\|aiff\|flac` | formato; senza flag vale l'estensione di `-o` |
| `--bit-depth 32f\|24` | float32 (default) o PCM 24 bit |
| `--normalize` | porta il picco a −1 dBFS a fine render |

Con il Makefile: `make render SCORE=brano.yaml` e `make tests`.

L'output diagnostico va letto sempre:

```
seed di sessione (generato): 1783012731311486400 -- aggiungi 'seed: ...' alla partitura per riprodurre
picco: -6.53 dBFS
```

Se compare `CLIPPING: picco +3.01 dBFS -- riduci master_volume di almeno
3.01 dB`, il mix supera il fondo scala: con l'uscita float32 il *file* è
comunque integro, ma qualunque player lo distorcerà. Rimedi, in ordine di
pulizia: abbassare `master_volume`, abbassare i `volume` dei layer, oppure
`--normalize` per il risultato rapido.

---

## 7. Leggere gli errori

Gli errori di partitura fermano il render *prima* di produrre audio
sbagliato, e dicono sempre cosa e dove:

| Errore | Significa | Rimedio tipico |
|---|---|---|
| `ParameterBoundError: Parametro 'volume' fuori bounds: value=99.0 non rientra in [-120.0, 12.0]` | valore fuori dai limiti (vale anche per i singoli punti di un envelope) | correggi il numero |
| `InvalidFieldValueError: 'fragment.duration' e 'fragment.rhythm' sono mutuamente esclusivi` | hai dichiarato due modi di dare la durata | tienine uno |
| `InvalidFieldValueError: strategia di selezione 'shuffle' sconosciuta (disponibili: random, rotation, sequential)` | refuso in un nome di strategia | copia dal messaggio |
| `FileNotFoundError: Nessun file audio nel pool: ...` | cartella vuota o percorso sbagliato | controlla `pool:` (il percorso è relativo a dove lanci il comando) |
| errore di parsing YAML con riga/colonna | indentazione o sintassi | controlla spazi e trattini in quella riga |

---

## 8. Orientarsi nel repository

```
audiolayers/
├── audiolayers/
│   ├── main.py                  # la CLI
│   ├── engine/render.py         # la pipeline: YAML → layers → mix → file
│   ├── core/fragment_sequence.py# onset+durate, criterio di stop
│   ├── parameters/              # bounds, schema+default, Parameter, parser
│   ├── envelopes/               # Envelope e builder delle forme YAML
│   ├── strategies/              # durata, selezione, overflow, inviluppo
│   ├── audio/                   # caricamento+resampling, pan mid/side
│   └── shared/                  # seeding namespaced, errori
├── tests/                       # unit / integration / golden / e2e
├── docs/
│   ├── manuale.md               # questo file
│   ├── reference/               # yaml.md, cli.md (specifica asciutta)
│   ├── explanation/             # pge-analysis.md (roadmap evolutiva)
│   ├── plans/done/              # il plan di bootstrap con le decisioni D1–D20
│   └── ideas/                   # appunti dalle sessioni
└── Makefile                     # make tests, make render SCORE=...
```

Il principio architetturale unico: ogni famiglia di algoritmi
intercambiabili (come si scelgono i file, come si generano le durate,
cosa fare a fine file, che forma dare ai frammenti) è una **Strategy**
dietro un'interfaccia — aggiungere una variante non tocca il resto.

---

## 9. I test

```bash
make tests          # tutta la suite
make unit           # solo unit (le Strategy in isolamento)
make integration    # pipeline YAML → buffer
make golden         # render confrontati con riferimenti versionati
make e2e            # la CLI vera, via subprocess
```

I **golden** meritano una nota: tre partiture fissate vengono
renderizzate e confrontate campione-per-campione con file di riferimento
committati. Se modifichi il motore e il suono *deve* cambiare, rigenera i
riferimenti con `python tests/golden/regenerate_references.py` e
ascoltali prima di committarli: sono l'orecchio automatico del progetto.

---

## 10. Per approfondire

- [reference/yaml.md](reference/yaml.md) — la specifica completa del formato,
  con la tabella dei bounds e l'esempio a due layer commentato
- [reference/cli.md](reference/cli.md) — la CLI in dettaglio
- [explanation/pge-analysis.md](explanation/pge-analysis.md) — da dove viene
  l'architettura (PythonGranularEngine) e la roadmap delle prossime
  iniezioni: envelope cubic, dephase, multi-voice, trasposizione…
- [plans/done/2026-07-02-001-project-bootstrap-plan.md](plans/done/2026-07-02-001-project-bootstrap-plan.md)
  — il registro delle 20 decisioni di design con le motivazioni
