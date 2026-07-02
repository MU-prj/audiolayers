"""CLI di audiolayers: renderizza una partitura YAML in un file audio.

Uso: python -m src.main SCORE.yaml -o OUT.wav
"""

import argparse
from pathlib import Path

from src.engine.render import render_score


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="audiolayers",
        description="Renderizza una partitura YAML in un file audio.",
    )
    parser.add_argument("score", type=Path, help="partitura YAML")
    parser.add_argument("-o", "--output", type=Path, required=True,
                        help="file audio di output")
    parser.add_argument("--format", choices=("wav", "aiff", "flac"),
                        default=None,
                        help="formato di output (default: dall'estensione, "
                             "altrimenti wav)")
    parser.add_argument("--bit-depth", choices=("32f", "24"), default="32f",
                        help="32f = float32 (default), 24 = PCM 24 bit")
    parser.add_argument("--normalize", action="store_true",
                        help="normalizza il picco a -1 dBFS (mai di default)")
    args = parser.parse_args(argv)

    render_score(args.score, args.output, output_format=args.format,
                 bit_depth=args.bit_depth, normalize=args.normalize)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
