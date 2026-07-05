"""CLI di audiolayers: renderizza una partitura YAML in un file audio.

Uso: python -m audiolayers.main SCORE.yaml -o OUT.wav
"""

import argparse
from pathlib import Path

from audiolayers.engine.render import render_score


def main(argv=None, *, client=None) -> int:
    # `client` (iniettabile, stile archivedigger.api): Internet Archive
    # finto nei test, quello vero di default; usato solo con --dig.
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
    parser.add_argument("--dig", action="store_true",
                        help="popola i pool mancanti da Internet Archive "
                             "(archivedigger) prima del render")
    args = parser.parse_args(argv)

    if args.dig:
        from audiolayers.provisioning.pool_source import provision_score
        provision_score(args.score, client=client)

    render_score(args.score, args.output, output_format=args.format,
                 bit_depth=args.bit_depth, normalize=args.normalize)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
