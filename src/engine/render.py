"""Pipeline di rendering: partitura YAML → buffer stereo → file audio.

Dal M5 il layer è cablato sul sistema dichiarativo: parametri con
tendency mask (D5), durate da Strategy (D8), onset da fill_factor +
distribution con stop senza mozzatura (D2, D3, D7), seeding namespaced
con seed di sessione da timestamp sempre loggato (D14).
"""

import time as _time
from pathlib import Path

import numpy as np
import soundfile as sf
import yaml

from src.audio.pan import pan_stereo
from src.audio.source_loader import load_mono
from src.core.fragment_sequence import build_fragment_sequence
from src.parameters.parser import create_layer_parameters
from src.shared.seeding import rng_for
from src.strategies.duration_strategy import build_duration_strategy
from src.strategies.fragment_envelope import build_fragment_envelope
from src.strategies.overflow_strategy import build_overflow_strategy
from src.strategies.selection_strategy import build_selection_strategy

DEFAULT_SAMPLE_RATE = 48000

AUDIO_EXTENSIONS = (".wav", ".aif", ".aiff", ".flac")


def render_score(score_path: Path, output_path: Path, *,
                 output_format: str | None = None,
                 bit_depth: str = "32f",
                 normalize: bool = False) -> None:
    """Renderizza la partitura e scrive il file di output.

    Default: WAV float32 (D1). `output_format` (wav/aiff/flac) e
    `bit_depth` (32f/24) arrivano dalla CLI; `normalize` porta il picco
    a -1 dBFS (mai di default, D16).
    """
    data = yaml.safe_load(Path(score_path).read_text(encoding="utf-8"))
    sample_rate = int(data.get("sample_rate", DEFAULT_SAMPLE_RATE))
    seed = _resolve_seed(data)

    active_layers = _filter_solo_mute(data["layers"])

    # Ogni layer ha un onset sulla timeline globale (D15).
    placed = []
    for layer in active_layers:
        onset_frames = round(float(layer.get("onset", 0.0)) * sample_rate)
        placed.append((onset_frames, _render_layer(layer, sample_rate, seed)))

    total_frames = max(offset + len(buf) for offset, buf in placed)
    mix = np.zeros((total_frames, 2), dtype=np.float64)
    for offset, buf in placed:
        mix[offset:offset + len(buf)] += buf

    mix = _apply_master(mix, data.get("master_volume", 0.0), sample_rate)
    mix = _report_peak_and_normalize(mix, normalize)

    fmt, subtype = _resolve_format(output_path, output_format, bit_depth)
    sf.write(str(output_path), mix.astype(np.float32), sample_rate,
             format=fmt, subtype=subtype)


def _filter_solo_mute(layers: list) -> list:
    """Convenzione PGE: se esistono layer in solo, suonano solo quelli;
    altrimenti suonano tutti tranne i mutati."""
    def flag(layer, name):
        return name in layer and layer[name] is not False

    soloed = [l for l in layers if flag(l, "solo")]
    if soloed:
        return soloed
    return [l for l in layers if not flag(l, "mute")]


def _apply_master(mix: np.ndarray, master_volume,
                  sample_rate: int) -> np.ndarray:
    """master_volume in dB, scalare o envelope (curva per-campione)."""
    from src.envelopes.envelope import Envelope
    from src.envelopes.envelope_builder import build_envelope

    master = build_envelope(master_volume)
    if isinstance(master, Envelope):
        times = np.arange(len(mix)) / sample_rate
        gain = 10.0 ** (master.evaluate_array(times) / 20.0)
        return mix * gain[:, None]
    return mix * (10.0 ** (master / 20.0))


def _report_peak_and_normalize(mix: np.ndarray,
                               normalize: bool) -> np.ndarray:
    """Misura il picco e lo RIPORTA (D16); --normalize opzionale."""
    peak = float(np.abs(mix).max())
    if peak == 0.0:
        print("picco: silenzio assoluto")
        return mix
    peak_db = 20.0 * np.log10(peak)
    if peak > 1.0:
        print(f"CLIPPING: picco {peak_db:+.2f} dBFS "
              f"-- riduci master_volume di almeno {peak_db:.2f} dB"
              + (" (o usa --normalize)" if not normalize else ""))
    else:
        print(f"picco: {peak_db:+.2f} dBFS")
    if normalize:
        target = 10.0 ** (-1.0 / 20.0)  # -1 dBFS
        mix = mix * (target / peak)
        print("normalizzato a -1.00 dBFS")
    return mix


_FORMATS = {
    ".wav": "WAV", ".aiff": "AIFF", ".aif": "AIFF", ".flac": "FLAC",
}


def _resolve_format(output_path: Path, output_format: str | None,
                    bit_depth: str) -> tuple[str, str]:
    """Formato dal flag CLI, o dall'estensione, o WAV (D1)."""
    if output_format is not None:
        fmt = output_format.upper()
        if fmt == "AIF":
            fmt = "AIFF"
    else:
        fmt = _FORMATS.get(Path(output_path).suffix.lower(), "WAV")
    # FLAC non supporta il float: sempre PCM 24 bit.
    if fmt == "FLAC" or bit_depth == "24":
        return fmt, "PCM_24"
    return fmt, "FLOAT"


def _resolve_seed(data: dict):
    """Seed dalla partitura; assente → da timestamp, SEMPRE loggato (D14)."""
    if "seed" in data and data["seed"] is not None:
        return data["seed"]
    seed = _time.time_ns()
    # Solo ASCII nell'output CLI: le console Windows in pipe si strozzano
    # su caratteri non-ASCII (stessa lezione dei messaggi d'errore).
    print(f"seed di sessione (generato): {seed} "
          f"-- aggiungi 'seed: {seed}' alla partitura per riprodurre")
    return seed


def _render_layer(layer: dict, sample_rate: int, seed) -> np.ndarray:
    """Renderizza un layer: sequenza di frammenti → timeline stereo."""
    layer_id = layer.get("layer_id", "layer")
    target_duration = float(layer["duration"])
    time_mode = layer.get("time_mode", "absolute")

    params = create_layer_parameters(
        layer, layer_id=layer_id, duration=target_duration, seed=seed,
        time_mode=time_mode,
    )
    duration_strategy = build_duration_strategy(
        layer.get("fragment", {}), layer_id=layer_id,
        duration=target_duration, seed=seed, time_mode=time_mode,
    )
    fragments = build_fragment_sequence(
        duration_strategy=duration_strategy,
        fill_factor=params["fill_factor"],
        distribution=params["distribution"],
        target_duration=target_duration,
        rng=rng_for(seed, layer_id, "onset"),
    )

    pool_files = _scan_pool(Path(layer["pool"]))
    # Precarica il pool una volta sola (mono, al SR di progetto, D13).
    sources = [load_mono(p, sample_rate) for p in pool_files]
    selection = build_selection_strategy(
        layer.get("selection", {}), pool_size=len(sources),
        layer_id=layer_id, seed=seed,
    )
    overflow = build_overflow_strategy(layer.get("pointer", {}))
    envelope = build_fragment_envelope(layer.get("fragment", {}))

    extent = max(f.onset + f.duration for f in fragments)
    buffer = np.zeros((round(extent * sample_rate), 2), dtype=np.float64)

    for index, frag in enumerate(fragments):
        # Quale file suona questo frammento lo decide la Strategy (D6).
        source = sources[selection.select(index)]
        # Punto di lettura [0,1] → posizione assoluta nel file (D9),
        # indipendente dalla durata; l'overflow decide la Strategy.
        start_norm = params["pointer_start"].get_value(frag.onset)
        start_frame = round(start_norm * len(source))
        segment = overflow.read(source, start_frame,
                                round(frag.duration * sample_rate))

        # La voce del frammento (M8): gain dB (D10) → inviluppo
        # anti-click (D11) → pan mid/side (D12). I parametri sono
        # campionati al tempo di posa, con le loro tendency mask.
        gain = 10.0 ** (params["volume"].get_value(frag.onset) / 20.0)
        shaped = envelope.apply(segment, sample_rate) * gain
        stereo = pan_stereo(shaped, params["pan"].get_value(frag.onset))

        start = round(frag.onset * sample_rate)
        end = min(start + len(stereo), len(buffer))
        buffer[start:end] += stereo[: end - start]

    return buffer


def _scan_pool(pool_dir: Path) -> list[Path]:
    """File audio del pool, in ordine alfabetico stabile."""
    files = sorted(
        p for p in pool_dir.iterdir()
        if p.suffix.lower() in AUDIO_EXTENSIONS
    )
    if not files:
        raise FileNotFoundError(f"Nessun file audio nel pool: {pool_dir}")
    return files
