"""Il pool: la cartella dei file sorgente di un layer.

Unico punto che sa cos'è un pool valido — estensioni ammesse, ordine di
scansione, idoneità per durata. Render e provisioning importano da qui:
il confine tra i due sottosistemi passa per questo modulo, non per i
privati dell'uno o dell'altro.
"""

from pathlib import Path

import soundfile as sf

AUDIO_EXTENSIONS = (".wav", ".aif", ".aiff", ".flac")


def scan_pool(pool_dir: Path) -> list[Path]:
    """File audio del pool, in ordine alfabetico stabile.

    Pool inesistente o senza file audio → FileNotFoundError esplicito:
    meglio fermarsi subito che renderizzare silenzio.
    """
    pool_dir = Path(pool_dir)
    if not pool_dir.is_dir():
        raise FileNotFoundError(f"Cartella pool inesistente: {pool_dir}")
    files = sorted(
        p for p in pool_dir.iterdir()
        if p.suffix.lower() in AUDIO_EXTENSIONS
    )
    if not files:
        raise FileNotFoundError(f"Nessun file audio nel pool: {pool_dir}")
    return files


def count_suitable_files(pool_dir: Path, *, min_duration: float) -> int:
    """Quanti file del pool durano almeno `min_duration` secondi.

    La durata è quella reale letta dall'header (non metadati esterni).
    Cartella assente o vuota → 0: il chiamante deciderà di scaricare.
    """
    pool_dir = Path(pool_dir)
    if not pool_dir.is_dir():
        return 0
    count = 0
    for path in pool_dir.iterdir():
        if path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        info = sf.info(str(path))
        if info.frames / info.samplerate >= min_duration:
            count += 1
    return count
