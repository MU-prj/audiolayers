"""Unit — seeding namespaced (D14, lezione da PGE#154).

Ogni componente stocastica riceve un RNG derivato dal proprio NOME
(seed, layer_id, component), mai dalla posizione dei draw: solo/mute,
cache e refactor non possono alterare i valori delle altre componenti.
"""

import numpy as np

from src.shared.seeding import rng_for


def test_stesso_nome_stessa_sequenza():
    a = rng_for(42, "layer1", "fragment_duration").random(8)
    b = rng_for(42, "layer1", "fragment_duration").random(8)
    assert np.array_equal(a, b)


def test_componenti_diverse_sequenze_indipendenti():
    dur = rng_for(42, "layer1", "fragment_duration").random(8)
    vol = rng_for(42, "layer1", "volume").random(8)
    assert not np.array_equal(dur, vol)


def test_layer_diversi_sequenze_indipendenti():
    l1 = rng_for(42, "layer1", "volume").random(8)
    l2 = rng_for(42, "layer2", "volume").random(8)
    assert not np.array_equal(l1, l2)


def test_seed_diversi_sequenze_diverse():
    s42 = rng_for(42, "layer1", "volume").random(8)
    s43 = rng_for(43, "layer1", "volume").random(8)
    assert not np.array_equal(s42, s43)


def test_seed_stringa_e_zero_sono_validi():
    assert rng_for("mio-brano", "l", "c") is not None
    a = rng_for(0, "l", "c").random(4)
    b = rng_for(0, "l", "c").random(4)
    assert np.array_equal(a, b)
