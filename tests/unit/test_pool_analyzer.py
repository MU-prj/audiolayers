"""Unit — analyzer dei requisiti di pool (plan 002, D-P2/D-P3).

L'analyzer replica la costruzione della sequenza di frammenti del render
(stesso seed, stesso namespacing) e ne ricava i requisiti per il pool:
quanti file servono e quanto devono durare.
"""

import pytest

from audiolayers.provisioning.analyzer import (PoolRequirements, analyze_layer,
                                       apply_policy)
from audiolayers.shared.exceptions import InvalidFieldValueError


class TestApplyPolicy:
    """Issue #8: modalità di selezione file e politiche automatiche."""

    REQ = PoolRequirements(files_needed=120, min_file_duration=1.0,
                           max_file_duration=10.0)

    def test_per_fragment_default_invariato(self):
        assert apply_policy(self.REQ, {}) == self.REQ

    def test_fixed_pool_di_n_file_che_ciclano(self):
        out = apply_policy(self.REQ, {"mode": "fixed", "count": 20})
        assert out.files_needed == 20

    def test_threshold_variety_come_frazione(self):
        out = apply_policy(self.REQ, {"mode": "threshold", "variety": 0.5})
        assert out.files_needed == 60

    def test_threshold_files_minimo_esplicito_vince(self):
        out = apply_policy(self.REQ, {"mode": "threshold",
                                      "variety": 0.1, "count": 30})
        assert out.files_needed == 30

    def test_margine_sul_minimo_e_max_derivato(self):
        out = apply_policy(self.REQ, {"min_margin": 1.5, "max_factor": 20})
        assert out.min_file_duration == pytest.approx(1.5)
        assert out.max_file_duration == pytest.approx(30.0)

    def test_max_derivato_mai_sotto_il_tetto_base(self):
        """Grani corti: il max non scende sotto i 10 s storici."""
        req = PoolRequirements(10, 0.05, 10.0)
        out = apply_policy(req, {"max_factor": 20})
        assert out.max_file_duration == pytest.approx(10.0)

    def test_mode_sconosciuta_errore(self):
        with pytest.raises(InvalidFieldValueError, match="mode"):
            apply_policy(self.REQ, {"mode": "boh"})


class TestAnalyzeLayer:
    def test_layer_deterministico_conta_frammenti_e_durata_massima(self):
        """duration 2 s, frammenti fissi da 0.5 s back-to-back → 4 file,
        ogni file deve durare almeno 0.5 s."""
        layer = {
            "layer_id": "det",
            "duration": 2.0,
            "fill_factor": 1.0,
            "fragment": {"duration": 0.5},
        }
        req = analyze_layer(layer, seed=1)
        assert req.files_needed == 4
        assert req.min_file_duration == pytest.approx(0.5)

    def test_envelope_crescente_richiede_il_frammento_piu_lungo(self):
        """Partitura di riferimento: 1 ms → 1 s su 60 s. Il requisito di
        durata è quello del frammento più lungo (vicino ma sotto 1 s).
        Il conteggio è dominato dai frammenti corti iniziali:
        N = ∫ dt/dur(t) ≈ 60·ln(1000)/0.999 ≈ 415."""
        layer = {
            "layer_id": "stream",
            "duration": 60.0,
            "fill_factor": 1.0,
            "distribution": 0.0,
            "fragment": {"duration": [[0, 0.001], [60, 1.0]]},
        }
        req = analyze_layer(layer, seed=20260703)
        assert 0.9 < req.min_file_duration <= 1.0
        assert 400 <= req.files_needed <= 430
        assert req.max_file_duration == pytest.approx(10.0)

    def test_stesso_seed_stessi_requisiti_con_range_casuale(self):
        """Con duration_range il conteggio dipende dai draw: stesso seed
        → stessi requisiti (l'analyzer replica il render, non stima)."""
        layer = {
            "layer_id": "rnd",
            "duration": 10.0,
            "fragment": {"duration": 0.4, "duration_range": 0.3},
        }
        first = analyze_layer(layer, seed=42)
        second = analyze_layer(layer, seed=42)
        assert first == second
