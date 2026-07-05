"""Rigenera i riferimenti golden dopo un cambiamento INTENZIONALE del
motore. Ascolta/ispeziona i nuovi file prima di committarli.

    python tests/golden/regenerate_references.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from audiolayers.engine.render import render_score  # noqa: E402
from tests.golden.golden_common import (REFERENCES_DIR, build_pool,  # noqa: E402
                                        materialize_score, score_names)


def main() -> None:
    REFERENCES_DIR.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        pool = build_pool(tmp_path)
        for name in score_names():
            score = materialize_score(name, pool, tmp_path)
            reference = REFERENCES_DIR / name.replace(".yaml", ".wav")
            render_score(score, reference)
            print(f"rigenerato: {reference}")


if __name__ == "__main__":
    main()
