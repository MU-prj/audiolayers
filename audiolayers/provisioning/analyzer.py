"""Analyzer dei requisiti di pool (plan 002, D-P2/D-P3).

Non stima: costruisce lo stesso LayerPlan del render (stesse Strategy,
stesso seed namespaced), quindi il conteggio e la durata massima
coincidono con quello che il render produrrà.
"""

from dataclasses import dataclass

from audiolayers.core.layer_plan import build_layer_plan

#: Tetto (secondi) alla durata dei file da scaricare (D-P3, per ora fisso).
MAX_FILE_DURATION = 10.0


@dataclass(frozen=True)
class PoolRequirements:
    """Cosa serve al pool perché il layer suoni come da partitura."""

    files_needed: int
    min_file_duration: float
    max_file_duration: float


def apply_policy(req: PoolRequirements, provision: dict) -> PoolRequirements:
    """Applica al fabbisogno grezzo le politiche del blocco provision
    (issue #8): modalità di selezione file e margini automatici.

    - `mode: per-fragment` (default): 1 file per frammento;
    - `mode: fixed` + `count: N`: pool di N file che ciclano;
    - `mode: threshold`: `variety` (0..1, frazione del fabbisogno) e/o
      `count` (minimo esplicito) — vince il maggiore;
    - `min_margin`: moltiplicatore sulla durata minima richiesta;
    - `max_factor`: max = min × factor, mai sotto il tetto base.
    """
    import math

    from audiolayers.shared.exceptions import InvalidFieldValueError

    mode = provision.get("mode", "per-fragment")
    files_needed = req.files_needed
    if mode == "fixed":
        files_needed = max(1, int(provision.get("count", 1)))
    elif mode == "threshold":
        by_variety = math.ceil(
            req.files_needed * float(provision.get("variety", 1.0)))
        files_needed = max(int(provision.get("count", 0)), by_variety, 1)
    elif mode != "per-fragment":
        raise InvalidFieldValueError(
            f"provision.mode '{mode}' sconosciuta "
            f"(disponibili: fixed, per-fragment, threshold)")

    min_d = req.min_file_duration * float(provision.get("min_margin", 1.0))
    max_d = max(req.max_file_duration,
                min_d * float(provision.get("max_factor", 1.0)))
    return PoolRequirements(files_needed=files_needed,
                            min_file_duration=min_d,
                            max_file_duration=max_d)


def analyze_layer(layer: dict, seed) -> PoolRequirements:
    """Requisiti di pool per un layer: 1 file per frammento (D-P2),
    ogni file lungo almeno quanto il frammento più lungo (D-P3)."""
    fragments = build_layer_plan(layer, seed).fragments
    return PoolRequirements(
        files_needed=len(fragments),
        min_file_duration=max(f.duration for f in fragments),
        max_file_duration=MAX_FILE_DURATION,
    )
