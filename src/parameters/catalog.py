"""Catalogo dei parametri: LA fonte unica per motore e GUI (deepening D1).

Ogni voce dichiara path YAML, etichetta, bounds, default, enum,
env-abilità e spiegazione. I valori NON sono copie: bounds dal registry
(`parameter_definitions`), enum dai registri delle Strategy, default
dalle costanti del motore. La GUI si genera da `/api/params`: aggiungere
o cambiare un parametro qui si riflette ovunque, la divergenza tra
Python e JavaScript non è più possibile.

`ui` è il range comodo per gli slider (sottoinsieme dei bounds duri):
il campo numerico accetta comunque tutto ciò che i bounds permettono.
"""

from src.parameters.parameter_definitions import get_parameter_definition
from src.strategies.fragment_envelope import (DEFAULT_ATTACK,
                                              DEFAULT_RELEASE,
                                              available_envelopes)
from src.strategies.overflow_strategy import available_overflow_strategies
from src.strategies.selection_strategy import available_selection_strategies


def _num(path, label, bounds_name, default, *, env=True, step=0.01,
         ui=None, mode=None, info=""):
    """Voce numerica coi bounds presi dal registry del motore."""
    b = get_parameter_definition(bounds_name)
    entry = {"path": path, "label": label, "kind": "float",
             "min": b.min_val, "max": b.max_val, "step": step,
             "default": default, "env": env, "info": info}
    if ui:
        entry["ui"] = {"min": ui[0], "max": ui[1]}
    if mode:
        entry["mode"] = mode
    return entry


def _free(path, label, default, *, kind="float", env=False, step=0.01,
          minimo=None, massimo=None, ui=None, options=None, mode=None,
          info=""):
    """Voce senza registry (enum, testo, o numerica coi bounds inline)."""
    entry = {"path": path, "label": label, "kind": kind,
             "default": default, "env": env, "info": info}
    if minimo is not None:
        entry["min"] = minimo
    if massimo is not None:
        entry["max"] = massimo
    if kind == "float":
        entry["step"] = step
    if ui:
        entry["ui"] = {"min": ui[0], "max": ui[1]}
    if options is not None:
        entry["options"] = options
    if mode:
        entry["mode"] = mode
    return entry


def catalog() -> dict:
    """Il catalogo completo, JSON-serializzabile: global/layer/provision."""
    return {
        "global": [
            _free("sample_rate", "sample rate", 48000, kind="select",
                  options=[44100, 48000, 96000],
                  info="Frequenza di campionamento del progetto. Le sorgenti "
                       "vengono ricampionate in ingresso (soxr VHQ)."),
            _free("seed", "seed", 424242, kind="int",
                  info="Riproducibilità: stesso seed → render identico bit "
                       "per bit. Ogni layer e parametro ha il suo generatore "
                       "derivato dal seed."),
            _num("master_volume", "master (dB)", "master_volume", 0.0,
                 step=0.5, ui=(-60, 12),
                 info="Guadagno sul mix finale, in dB. Come curva diventa "
                      "una dissolvenza globale per-campione."),
        ],
        "layer": [
            _free("onset", "onset (s)", 0.0, minimo=0.0, massimo=36000.0,
                  step=0.5, ui=(0, 300),
                  info="Quando il layer entra sulla timeline globale, in "
                       "secondi. Scalare per natura."),
            _free("duration", "durata (s)", 20.0, minimo=0.001,
                  massimo=36000.0, step=1, ui=(1, 300),
                  info="Durata-obiettivo del layer. Non può essere una "
                       "curva: è l'asse del tempo su cui corrono tutte le "
                       "altre curve. L'ultimo grano non viene mai mozzato, "
                       "quindi il layer può sforare di poco."),
            _free("time_mode", "time mode", "absolute", kind="select",
                  options=["absolute", "normalized"],
                  info="Tempi degli envelope del layer: absolute = secondi; "
                       "normalized = frazioni 0..1 scalate sulla durata "
                       "(curve riusabili su layer di durate diverse)."),
            _num("fragment.duration", "grano (s)", "fragment_duration", 0.5,
                 step=0.001, ui=(0.001, 2),
                 info="Durata di ogni grano, in secondi. Come curva fa "
                      "accelerare/rallentare il flusso. In modalità ritmica "
                      "resta attiva: il ritmo decide QUANDO, questa QUANTO "
                      "(staccato granulare)."),
            _num("fragment.duration_range", "grano ± (s)",
                 "fragment_duration", 0.0, step=0.001, ui=(0, 1),
                 info="Variazione casuale della durata del grano attorno al "
                      "valore base. 0 = tutti i grani uguali."),
            _free("fragment.rhythm.bpm", "bpm", 120, env=True, step=1,
                  minimo=1.0, massimo=1000.0, ui=(20, 300), mode="rhythm",
                  info="Velocità del pattern ritmico. Come curva = "
                       "accelerando/ritardando continui."),
            _free("fragment.rhythm.pattern", "pattern",
                  [0.25, 0.125, 0.125], kind="numlist", mode="rhythm",
                  info="Valori ritmici ciclici in frazioni di semibreve: "
                       "0.25 = semiminima (un movimento), 0.125 = croma, "
                       "0.0625 = semicroma. Separati da virgola."),
            _free("fragment.envelope", "inviluppo", "raised_cosine",
                  kind="select", options=available_envelopes(),
                  info="Forma d'ampiezza del grano: raised_cosine = campana "
                       "morbida anti-click; rectangle = nessuna sagomatura "
                       "(bordi netti)."),
            _num("fragment.attack", "attack (s)", "fragment_attack",
                 DEFAULT_ATTACK, env=False, step=0.001, ui=(0, 0.1),
                 info="Fade-in del grano in secondi (anti-click). Scalare "
                      "nel motore."),
            _num("fragment.release", "release (s)", "fragment_release",
                 DEFAULT_RELEASE, env=False, step=0.001, ui=(0, 0.1),
                 info="Fade-out del grano in secondi (anti-click). Scalare "
                      "nel motore."),
            _num("fill_factor", "fill factor", "fill_factor", 1.0,
                 step=0.05, ui=(0.05, 5),
                 info="Densità: intervallo tra i grani = durata grano ÷ "
                      "fill factor. 1 = grani uno dietro l'altro; sotto 1 = "
                      "silenzi; sopra 1 = sovrapposizioni (crossfade "
                      "emergenti)."),
            _num("fill_factor_range", "fill factor ±", "fill_factor", 0.0,
                 step=0.05, ui=(0, 2.5),
                 info="Variazione casuale del fill factor per grano: valore "
                      "estratto uniformemente in [base−range, base+range] "
                      "(tendency mask di Truax)."),
            _num("distribution", "distribution", "distribution", 0.0,
                 ui=(0, 2),
                 info="Regolarità del tempo: 0 = metronomo, 1 = asincrono "
                      "(Truax: 0..2× il sincrono), oltre 1 lo spread si "
                      "amplifica fino a 0..4× — grappoli e buchi marcati."),
            _num("pointer.start", "pointer", "pointer_start", 0.0,
                 info="Punto di lettura nel file sorgente: 0 = inizio, "
                      "0.5 = metà, 1 = fine. Come curva attraversa il file "
                      "lungo il brano (time-stretch granulare)."),
            _num("pointer.start_range", "pointer ±", "pointer_start", 0.0,
                 info="Variazione casuale del punto di lettura. 0.5 con "
                      "pointer 0.5 = ogni grano pesca ovunque nel file."),
            _free("pointer.overflow", "overflow", "clamp_back",
                  kind="select", options=available_overflow_strategies(),
                  info="Se il grano supera la fine del file: clamp_back "
                       "arretra del minimo necessario; loop riparte "
                       "dall'inizio; zero_pad completa con silenzio."),
            _free("selection.strategy", "selezione", "sequential",
                  kind="select", options=available_selection_strategies(),
                  info="Quale file suona ogni grano: sequential = in ordine "
                       "alfabetico ciclando; rotation = permutazione casuale "
                       "per giro (ogni file una volta); random = estrazioni "
                       "indipendenti."),
            _num("volume", "volume (dB)", "volume", 0.0, step=0.5,
                 ui=(-60, 12),
                 info="Guadagno del layer in dB, campionato al momento di "
                      "posa di ogni grano. Come curva = crescendo/"
                      "diminuendo."),
            _num("volume_range", "volume ± (dB)", "volume", 0.0, step=0.5,
                 ui=(0, 12),
                 info="Variazione casuale del volume per grano, in ±dB: "
                      "respiro dinamico."),
            _free("pan", "pan (°)", 0.0, env=True, step=1, ui=(-360, 360),
                  info="Posizione stereo in gradi: 0 = centro, +45 = tutto "
                       "a sinistra, −45 = tutto a destra. Spazio circolare: "
                       "una curva sempre crescente fa RUOTARE il suono."),
            _free("pan_range", "pan ± (°)", 0.0, env=True, step=1,
                  minimo=0.0, ui=(0, 180),
                  info="Sparpagliamento stereo casuale attorno al pan, in "
                       "±gradi."),
        ],
        "provision": [
            _free("provision.search.license", "licenza", "cc",
                  kind="select",
                  options=["cc", "publicdomain", "cc-commercial", "any"],
                  info="Diritti d'uso dei file cercati su Internet Archive: "
                       "cc = Creative Commons, publicdomain = pubblico "
                       "dominio, cc-commercial = CC senza clausola NC, "
                       "any = nessun filtro."),
            _free("provision.search.collection", "collection", [],
                  kind="list",
                  info="Collezioni di Internet Archive in cui cercare "
                       "(separate da virgola). Vuoto = tutte. Verifica che "
                       "la collection esista: nomi sbagliati = zero "
                       "risultati."),
            _free("provision.search.subject", "subject", [], kind="list",
                  info="Tag/argomenti degli item (separati da virgola), "
                       "es. nature, ambient."),
            _free("provision.search.query", "query lucene", "", kind="text",
                  info="Via di fuga: sintassi Lucene grezza aggiunta alla "
                       "ricerca. Es. format:(\"WAVE\" OR \"Flac\") per item "
                       "che contengono file lossless."),
            _free("provision.files.prefer", "formati",
                  [["Flac", "WAVE", "AIFF"]], kind="listlist",
                  info="Formati preferiti (separati da virgola, a pari "
                       "merito). Il motore legge solo wav/aif/flac: niente "
                       "mp3. Quanti file scaricare e le durate min/max li "
                       "calcola l'analisi della partitura."),
        ],
    }


def catalog_entry(section: str, path: str) -> dict:
    """La voce di catalogo per `path` nella sezione data (KeyError se manca)."""
    for entry in catalog()[section]:
        if entry["path"] == path:
            return entry
    raise KeyError(f"{section}/{path} non nel catalogo")
