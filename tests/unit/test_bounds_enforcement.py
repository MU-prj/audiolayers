"""Unit — i bounds dichiarati vengono DAVVERO applicati (deepening D1b).

Prima master_volume era nel registry ma mai validato, e attack/release
non avevano bounds da nessuna parte: la sicurezza era illusoria.
"""

import numpy as np
import pytest
import soundfile as sf

from audiolayers.engine.render import render_score
from audiolayers.shared.exceptions import ParameterBoundError
from audiolayers.strategies.fragment_envelope import build_fragment_envelope


def write_score(tmp_path, master):
    pool = tmp_path / "pool"
    pool.mkdir()
    sf.write(str(pool / "a.wav"), np.zeros(48000, dtype=np.float32), 48000)
    score = tmp_path / "s.yaml"
    score.write_text(
        f"seed: 1\nmaster_volume: {master}\n"
        f"layers:\n  - duration: 1.0\n    pool: '{pool.as_posix()}/'\n"
        f"    fragment: {{duration: 0.5}}\n", encoding="utf-8")
    return score


class TestMasterVolume:
    def test_fuori_bounds_ferma_il_render(self, tmp_path):
        with pytest.raises(ParameterBoundError):
            render_score(write_score(tmp_path, 999), tmp_path / "o.wav")

    def test_envelope_fuori_bounds_ferma_il_render(self, tmp_path):
        with pytest.raises(ParameterBoundError):
            render_score(write_score(tmp_path, "[[0, 0], [10, 500]]"),
                         tmp_path / "o.wav")

    def test_valore_legale_passa(self, tmp_path):
        render_score(write_score(tmp_path, -6.0), tmp_path / "o.wav")
        assert (tmp_path / "o.wav").exists()


class TestAttackRelease:
    def test_attack_negativo_rifiutato(self):
        with pytest.raises(ParameterBoundError):
            build_fragment_envelope({"attack": -0.01})

    def test_release_oltre_il_bound_rifiutato(self):
        with pytest.raises(ParameterBoundError):
            build_fragment_envelope({"release": 3.0})

    def test_default_validi(self):
        build_fragment_envelope({})
