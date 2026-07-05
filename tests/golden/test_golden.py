"""Golden test (M10, D19): il render delle partiture fixture deve
coincidere col riferimento versionato, entro tolleranza float.

Se un cambiamento del motore è INTENZIONALE, rigenera i riferimenti:
    python tests/golden/regenerate_references.py
e ispeziona/ascolta i nuovi file prima di committarli.
"""

import numpy as np
import pytest
import soundfile as sf

from audiolayers.engine.render import render_score
from tests.golden.golden_common import (REFERENCES_DIR, build_pool,
                                        materialize_score, score_names)


@pytest.mark.golden
@pytest.mark.parametrize("score_name", score_names())
def test_render_coincide_col_riferimento(score_name, tmp_path):
    reference_path = REFERENCES_DIR / score_name.replace(".yaml", ".wav")
    assert reference_path.exists(), (
        f"riferimento mancante: {reference_path} "
        "(genera con: python tests/golden/regenerate_references.py)"
    )

    pool = build_pool(tmp_path)
    score = materialize_score(score_name, pool, tmp_path)
    out = tmp_path / "out.wav"
    render_score(score, out)

    rendered, sr_r = sf.read(str(out), always_2d=True)
    reference, sr_ref = sf.read(str(reference_path), always_2d=True)

    assert sr_r == sr_ref
    assert rendered.shape == reference.shape, (
        f"forma diversa: {rendered.shape} vs riferimento {reference.shape}"
    )
    max_diff = float(np.abs(rendered - reference).max())
    assert max_diff < 1e-5, (
        f"il render di {score_name} devia dal riferimento "
        f"(max diff = {max_diff:.2e})"
    )
