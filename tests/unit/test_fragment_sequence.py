"""Unit — sequenza dei frammenti (M5): onset da fill_factor +
distribution (D2, D3) con criterio di stop senza mozzatura (D7).

Il costruttore di sequenza accoppia durata e onset (dipendenza
sequenziale): frammento i → durata da DurationStrategy, poi
IOI = durata / F(t), miscelato col modello Truax di `distribution`.
"""

import numpy as np
import pytest

from audiolayers.core.fragment_sequence import FragmentSpec, build_fragment_sequence
from audiolayers.parameters.parser import create_parameter
from audiolayers.shared.seeding import rng_for
from audiolayers.strategies.duration_strategy import build_duration_strategies


def make_sequence(target=2.0, fragment_block=None, fill_factor=1.0,
                  distribution=0.0, seed=42, layer_id="l1"):
    kwargs = dict(layer_id=layer_id, duration=target, seed=seed)
    grain, ioi = build_duration_strategies(
        fragment_block or {"duration": 0.5}, **kwargs)
    return build_fragment_sequence(
        duration_strategy=grain,
        ioi_strategy=ioi,
        fill_factor=create_parameter("fill_factor", fill_factor, **kwargs),
        distribution=create_parameter("distribution", distribution, **kwargs),
        target_duration=target,
        rng=rng_for(seed, layer_id, "onset"),
    )


class TestRegimeDeterministico:
    def test_f1_frammenti_back_to_back(self):
        seq = make_sequence(target=2.0, fill_factor=1.0)
        assert [f.onset for f in seq] == pytest.approx([0.0, 0.5, 1.0, 1.5])
        assert all(f.duration == 0.5 for f in seq)

    def test_f_minore_di_uno_inserisce_silenzi(self):
        seq = make_sequence(target=2.0, fill_factor=0.5)  # IOI = 1.0
        assert [f.onset for f in seq] == pytest.approx([0.0, 1.0])

    def test_f_maggiore_di_uno_sovrappone(self):
        seq = make_sequence(target=1.0, fill_factor=2.0)  # IOI = 0.25
        assert [f.onset for f in seq] == pytest.approx([0.0, 0.25, 0.5, 0.75])

    def test_ultimo_frammento_mai_mozzato(self):
        """D7: l'estensione può sforare il target, mai troncare."""
        seq = make_sequence(target=1.8, fill_factor=1.0)
        last = seq[-1]
        assert last.onset < 1.8
        assert last.onset + last.duration == pytest.approx(2.0)  # sfora

    def test_f_envelope_infittisce_nel_tempo(self):
        seq = make_sequence(target=4.0,
                            fill_factor=[[0.0, 0.5], [4.0, 2.0]])
        iois = np.diff([f.onset for f in seq])
        assert all(np.diff(iois) < 0)  # IOI decrescenti: tessuto più fitto


class TestRegimeStocastico:
    def test_async_riproducibile_a_parita_di_seed(self):
        s1 = make_sequence(target=10.0, distribution=1.0, seed=7)
        s2 = make_sequence(target=10.0, distribution=1.0, seed=7)
        assert [f.onset for f in s1] == [f.onset for f in s2]

    def test_async_onsets_crescenti_e_dentro_il_target(self):
        seq = make_sequence(target=10.0, distribution=1.0)
        onsets = [f.onset for f in seq]
        assert all(b >= a for a, b in zip(onsets, onsets[1:]))
        assert all(o < 10.0 for o in onsets)

    def test_blend_intermedio_limita_gli_ioi(self):
        """d=0.5: IOI ∈ [0.5, 1.5] × IOI_sync (miscela lineare Truax)."""
        seq = make_sequence(target=30.0, distribution=0.5)
        iois = np.diff([f.onset for f in seq])
        sync = 0.5  # durata 0.5 / F 1.0
        assert all(0.5 * sync <= ioi <= 1.5 * sync + 1e-9 for ioi in iois)

    def test_distribution_envelope_da_metronomo_a_nuvola(self):
        seq = make_sequence(target=20.0,
                            distribution=[[0.0, 0.0], [20.0, 1.0]])
        iois = np.diff([f.onset for f in seq])
        # nella prima metà gli IOI sono quasi sincroni, nella seconda variano
        first, second = iois[: len(iois) // 2], iois[len(iois) // 2:]
        assert np.std(first) < np.std(second)


class TestGrigliaRitmicaConGranoIndipendente:
    def test_rhythm_decide_gli_onset_duration_la_lunghezza(self):
        """Griglia da 0.5 s (1/4 a 120), grani corti da 0.05 s: gli onset
        seguono il ritmo, le durate la tendency mask."""
        frags = make_sequence(target=2.0, fragment_block={
            "duration": 0.05,
            "rhythm": {"bpm": 120, "pattern": [0.25]},
        })
        onsets = [round(f.onset, 6) for f in frags]
        assert onsets == [0.0, 0.5, 1.0, 1.5]
        assert all(abs(f.duration - 0.05) < 1e-9 for f in frags)


class TestDistributionEstrema:
    def test_oltre_uno_lo_spread_si_amplifica(self):
        """d=2: gli intervalli possono superare di molto il doppio
        dell'IOI sincrono (spread 0..4x), cosa impossibile con d=1."""
        def spread(dist):
            frags = make_sequence(target=60.0, distribution=dist,
                                  fragment_block={"duration": 0.5})
            iois = np.diff([f.onset for f in frags])
            return float(iois.max())

        assert spread(2.0) > 2.0 * 0.5 + 1e-6   # oltre il tetto di d=1
        assert spread(2.0) > spread(1.0)

    def test_fino_a_uno_comportamento_invariato(self):
        """d=1 resta il Truax classico: IOI in [0, 2x]. (I golden
        proteggono l'identita' bit a bit dei casi esistenti.)"""
        frags = make_sequence(target=60.0, distribution=1.0,
                              fragment_block={"duration": 0.5})
        iois = np.diff([f.onset for f in frags])
        assert iois.max() <= 1.0 + 1e-9
