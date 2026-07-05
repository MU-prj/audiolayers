"""Derivazione deterministica e namespaced degli RNG (D14).

Unica fonte di verità per la casualità del sistema. Ogni componente
stocastica (durata, volume, pan, selezione, …) riceve un generatore
derivato da (seed, layer_id, component) via SHA-256: deterministico,
indipendente da PYTHONHASHSEED e dall'ordine dei draw altrui.

Lezione appresa da PGE#154: MAI un RNG globale condiviso — renderebbe
i valori dipendenti da solo/mute, cache e ordine di valutazione.
"""

import hashlib

import numpy as np


def rng_for(seed, layer_id: str, component: str) -> np.random.Generator:
    """RNG dedicato e riproducibile per (seed, layer_id, component)."""
    digest = hashlib.sha256(
        f"{seed}:{layer_id}:{component}".encode()
    ).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], "little"))
