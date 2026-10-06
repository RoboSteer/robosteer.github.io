#!/usr/bin/env python3

import argparse
import pickle
import sys
import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

try:
    import librosa
except ModuleNotFoundError as exc:
    raise SystemExit(
        "librosa is required for utils/wav_to_audio29_pkl.py. "
        "Install project dependencies first, for example: pip install -r requirements.txt"
    ) from exc


AUDIO29_COLUMNS = [*(f"MFCC_{i}" for i in range(20)),
                   *(f"Chroma_{i}" for i in range(6)),
                   "Spectralflux_0",
                   "Beatactivation_0",
                   "Beat_0"]
SUPPORTED_AUDIO_SUFFIXES = {".wav", ".mp3"}
WARNING_ZSCORE_THRESHOLD = 8.0
DEFAULT_BEAT_ACTIVATION_MAX = 1.0
REPO_ROOT = Path(__file__).resolve().parents[1]
BEAT_ACTIVATION_SOFTNESS = 0.5
REFERENCE_BOUNDS_ROOT = REPO_ROOT / "data" / "motorica_dance"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "data" / "level1"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract 29 audio features at fixed FPS and save them as a pickle DataFrame."
    )
    parser.add_argument(
        "audio_path",
        type=Path,
        help="Input audio file (.wav or .mp3), or a directory to process in batch.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help=(
            "Output .pkl path for single-file input. "
            "For directory input, this must be an output directory and the source tree is mirrored under it."
        ),
    )
    parser.add_argument("--fps", type=int, default=30, help="Target frame rate.")
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=0,
        help="Optional internal resample rate. Defaults to 0, which keeps the native input sample rate.",
    )
    parser.add_argument("--n-fft", type=int, default=2048, help="FFT window size.")
    parser.add_argument(
        "--no-calibration",
        action="store_true",
        help="Disable feature calibration against existing audio29 reference files in the input audio directory.",
    )
    parser.add_argument("--reference-bounds-dir", type=Path, default=None,
                        help="Explicit reference feature directory; requires --no-calibration and disables automatic reference search.")
    args = parser.parse_args()
    if args.reference_bounds_dir is not None:
        if not args.no_calibration:
            parser.error("--reference-bounds-dir requires --no-calibration")
        args.reference_bounds_dir = args.reference_bounds_dir.expanduser().resolve()
        if not args.reference_bounds_dir.is_dir():
            parser.error("--reference-bounds-dir must be an existing directory")
    return args


def validate_audio_path(audio_path: Path):
    suffix = audio_path.suffix.lower()
    if suffix not in SUPPORTED_AUDIO_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_AUDIO_SUFFIXES))
        raise ValueError(f"Unsupported audio format: {audio_path.suffix or '<no suffix>'}. Expected one of: {supported}")


def validate_input_path(audio_path: Path):
    if not audio_path.exists():
        raise FileNotFoundError(f"Input path does not exist: {audio_path}")
    if audio_path.is_file():
        validate_audio_path(audio_path)
        return
    if not audio_path.is_dir():
        raise ValueError(f"Input path must be a file or directory: {audio_path}")


def iter_audio_paths(input_path: Path):
    if input_path.is_file():
        yield input_path
        return
    for path in sorted(input_path.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_AUDIO_SUFFIXES:
            yield path


def load_audio(audio_path: Path, sample_rate: int):
    sr_arg = sample_rate if sample_rate and sample_rate > 0 else None
    y, sr = librosa.load(audio_path, sr=sr_arg, mono=True)
    return y.astype(np.float32), sr


def compute_features(y: np.ndarray, sr: int, fps: int, n_fft: int):
    if sr % fps != 0:
        raise ValueError(f"sample_rate={sr} must be divisible by fps={fps}")

    hop_length = sr // fps
    win_length = n_fft

    stft = librosa.stft(
        y,
        n_fft=n_fft,
        hop_length=hop_length,
        win_length=win_length,
        center=False,
    )
    magnitude = np.abs(stft).astype(np.float32)
    power = (magnitude ** 2).astype(np.float32)

    mfcc = librosa.feature.mfcc(
        y=y,
        sr=sr,
        n_mfcc=20,
        n_fft=n_fft,
        hop_length=hop_length,
        win_length=win_length,
        center=False,
    ).astype(np.float32)

    # Match the stored dataset more closely by using unnormalized chroma from magnitude spectra.
    chroma12 = librosa.feature.chroma_stft(
        S=magnitude,
        sr=sr,
        norm=None,
    ).astype(np.float32)
    chroma6 = (chroma12[:6] + chroma12[6:12]).astype(np.float32)

    spectral_flux = np.zeros(magnitude.shape[1], dtype=np.float32)
    if magnitude.shape[1] > 1:
        delta = np.maximum(0.0, magnitude[:, 1:] - magnitude[:, :-1])
        spectral_flux[1:] = np.sum(delta, axis=0).astype(np.float32)

    beat_activation = librosa.onset.onset_strength(
        y=y,
        sr=sr,
        hop_length=hop_length,
        center=False,
    ).astype(np.float32)

    beat_binary = np.zeros_like(beat_activation, dtype=np.float32)
    _, beat_frames = librosa.beat.beat_track(
        onset_envelope=beat_activation,
        sr=sr,
        hop_length=hop_length,
        units="frames",
    )
    beat_frames = np.asarray(beat_frames, dtype=np.int64)
    beat_frames = beat_frames[(beat_frames >= 0) & (beat_frames < beat_binary.shape[0])]
    beat_binary[beat_frames] = 1.0

    n_frames = min(
        mfcc.shape[1],
        chroma6.shape[1],
        spectral_flux.shape[0],
        beat_activation.shape[0],
        beat_binary.shape[0],
    )
    if n_frames == 0:
        raise ValueError("No feature frames were extracted from the input audio.")

    features = np.concatenate(
        [
            mfcc[:, :n_frames].T,
            chroma6[:, :n_frames].T,
            spectral_flux[:n_frames, None],
            beat_activation[:n_frames, None],
            beat_binary[:n_frames, None],
        ],
        axis=1,
    ).astype(np.float32)

    time_index = pd.to_timedelta(np.arange(n_frames) / fps, unit="s")
    return pd.DataFrame(features, columns=AUDIO29_COLUMNS, index=time_index)


def iter_reference_pairs(data_dir: Path, fps: int, exclude_audio: Path):
    suffix = f"_00.audio29_{fps}fps.pkl"
    for pkl_path in sorted(data_dir.glob(f"*{suffix}")):
        audio_stem = pkl_path.name[: -len(suffix)]
        for audio_suffix in sorted(SUPPORTED_AUDIO_SUFFIXES):
            audio_path = data_dir / f"{audio_stem}{audio_suffix}"
            if not audio_path.exists():
                continue
            if audio_path.resolve() == exclude_audio.resolve():
                continue
            yield audio_path, pkl_path
            break


def calibration_cache_path(data_dir: Path, fps: int, n_fft: int):
    return data_dir / f"audio29_calibration_{fps}fps_nfft{n_fft}.pkl"


def collect_reference_bounds(search_root: Path, fps: int, exclude_pkl: Optional[Path] = None):
    pkl_paths = sorted(search_root.rglob(f"*.audio29_{fps}fps.pkl"))
    mins = []
    maxs = []
    exclude_resolved = exclude_pkl.resolve() if exclude_pkl is not None and exclude_pkl.exists() else None

    for pkl_path in pkl_paths:
        if exclude_resolved is not None and pkl_path.resolve() == exclude_resolved:
            continue
        with pkl_path.open("rb") as f:
            ref_df = pickle.load(f)
        if "Beatactivation_0" not in ref_df:
            continue
        series = ref_df["Beatactivation_0"].astype(np.float32)
        mins.append(float(series.min()))
        maxs.append(float(series.max()))

    if not mins:
        return None

    return {
        "ref_min": pd.Series({"Beatactivation_0": min(mins)}, dtype=np.float32),
        "ref_max": pd.Series({"Beatactivation_0": max(maxs)}, dtype=np.float32),
    }


def compute_calibration_stats(data_dir: Path, fps: int, n_fft: int, exclude_audio: Path):
    raw_frames = []
    ref_frames = []
    for audio_path, pkl_path in iter_reference_pairs(data_dir, fps, exclude_audio):
        y_ref, sr_ref = load_audio(audio_path, 0)
        raw_df = compute_features(y_ref, sr_ref, fps, n_fft)
        with pkl_path.open("rb") as f:
            ref_df = pickle.load(f)
        ref_df = ref_df[AUDIO29_COLUMNS].astype(np.float32)
        n_frames = min(len(raw_df), len(ref_df))
        if n_frames == 0:
            continue
        raw_frames.append(raw_df.iloc[:n_frames])
        ref_frames.append(ref_df.iloc[:n_frames])

    if not raw_frames:
        return None

    raw_all = pd.concat(raw_frames, axis=0)
    ref_all = pd.concat(ref_frames, axis=0)
    cols = [c for c in AUDIO29_COLUMNS if c != "Beat_0"]
    eps = 1e-6
    stats = {
        "columns": cols,
        "raw_mean": raw_all[cols].mean().astype(np.float32),
        "raw_std": raw_all[cols].std(ddof=0).clip(lower=eps).astype(np.float32),
        "ref_mean": ref_all[cols].mean().astype(np.float32),
        "ref_std": ref_all[cols].std(ddof=0).clip(lower=eps).astype(np.float32),
        "ref_min": ref_all[cols].min().astype(np.float32),
        "ref_max": ref_all[cols].max().astype(np.float32),
    }
    return stats


def load_or_compute_calibration_stats(data_dir: Path, fps: int, n_fft: int, exclude_audio: Path):
    cache_path = calibration_cache_path(data_dir, fps, n_fft)
    if cache_path.exists():
        with cache_path.open("rb") as f:
            return pickle.load(f)

    stats = compute_calibration_stats(data_dir, fps, n_fft, exclude_audio)
    if stats is None:
        return None

    with cache_path.open("wb") as f:
        pickle.dump(stats, f, protocol=pickle.HIGHEST_PROTOCOL)
    return stats


def apply_calibration(features_df: pd.DataFrame, stats):
    out_df = features_df.copy()
    cols = stats["columns"]
    raw_mean = stats["raw_mean"].reindex(cols)
    raw_std = stats["raw_std"].reindex(cols)
    ref_mean = stats["ref_mean"].reindex(cols)
    ref_std = stats["ref_std"].reindex(cols)
    out_df[cols] = ((out_df[cols] - raw_mean) / raw_std) * ref_std + ref_mean
    out_df["Beat_0"] = (out_df["Beat_0"] > 0.5).astype(np.float32)
    return out_df.astype(np.float32)


def apply_reference_bounds(features_df: pd.DataFrame, stats):
    out_df = features_df.copy()
    adjustment_messages = []

    ref_min = stats.get("ref_min")
    ref_max = stats.get("ref_max")

    if "Beatactivation_0" in out_df.columns:
        lower = 0.0
        upper = DEFAULT_BEAT_ACTIVATION_MAX
        if ref_min is not None and "Beatactivation_0" in ref_min.index:
            lower = max(lower, float(ref_min["Beatactivation_0"]))
        if ref_max is not None and "Beatactivation_0" in ref_max.index:
            upper = min(upper, max(lower, float(ref_max["Beatactivation_0"])))

        original = out_df["Beatactivation_0"].astype(np.float32)
        adjusted = original.clip(lower=lower)

        overflow = adjusted > upper
        if bool(overflow.any()):
            softness = max(upper * BEAT_ACTIVATION_SOFTNESS, 1e-6)
            delta = ((adjusted[overflow] - upper) / softness).astype(np.float32)
            adjusted.loc[overflow] = upper + softness * np.tanh(delta)
            adjustment_messages.append(
                f"Soft-compressed Beatactivation_0 above {upper:.4f} on {int(overflow.sum())} frames to stay close to the reference distribution."
            )

        underflow = original < lower
        if bool(underflow.any()):
            adjustment_messages.append(
                f"Raised Beatactivation_0 to the minimum reference bound {lower:.4f} on {int(underflow.sum())} frames."
            )

        out_df["Beatactivation_0"] = adjusted.astype(np.float32)

    return out_df.astype(np.float32), adjustment_messages


def summarize_features(features_df: pd.DataFrame):
    stats = features_df.agg(["min", "max", "mean", "std"]).T.fillna(0.0)
    return stats.astype(np.float32)


def warn_on_extreme_features(features_df: pd.DataFrame):
    summary = summarize_features(features_df)
    warnings_found = []

    beat_activation_max = float(summary.loc["Beatactivation_0", "max"])
    if beat_activation_max > 5.0:
        warnings_found.append(
            f"Beatactivation_0 max={beat_activation_max:.4f} is high and may produce out-of-distribution inputs for dance_LDA checkpoints."
        )

    for column in ["Spectralflux_0", "Beatactivation_0"]:
        col_std = float(summary.loc[column, "std"])
        col_mean = float(summary.loc[column, "mean"])
        col_max = float(summary.loc[column, "max"])
        if col_std > 1e-6:
            z_max = (col_max - col_mean) / col_std
            if z_max > WARNING_ZSCORE_THRESHOLD:
                warnings_found.append(
                    f"{column} max z-score={z_max:.2f} exceeds {WARNING_ZSCORE_THRESHOLD:.1f}; synthesis may become unstable."
                )

    return summary, warnings_found


def resolve_output_path(audio_path: Path, output: Optional[Path], fps: int, input_root: Optional[Path] = None):
    if output is not None:
        if input_root is not None:
            relative_parent = audio_path.parent.relative_to(input_root)
            return output / relative_parent / f"{audio_path.stem}.audio29_{fps}fps.pkl"
        return output
    if input_root is not None:
        relative_parent = audio_path.parent.relative_to(input_root)
        return DEFAULT_OUTPUT_ROOT / relative_parent / f"{audio_path.stem}.audio29_{fps}fps.pkl"
    return DEFAULT_OUTPUT_ROOT / f"{audio_path.stem}.audio29_{fps}fps.pkl"


def process_audio_path(audio_path: Path, args, output_path: Path):
    y, sr = load_audio(audio_path, args.sample_rate)
    features_df = compute_features(y, sr, args.fps, args.n_fft)
    clip_messages = []
    bound_stats = None

    if not args.no_calibration:
        stats = load_or_compute_calibration_stats(audio_path.parent, args.fps, args.n_fft, audio_path)
        if stats is not None:
            features_df = apply_calibration(features_df, stats)
            bound_stats = stats

    if args.reference_bounds_dir is not None:
        bound_stats = collect_reference_bounds(args.reference_bounds_dir, args.fps, exclude_pkl=output_path)
        if bound_stats is None:
            raise ValueError(f"No usable reference features in {args.reference_bounds_dir}")
    else:
        if bound_stats is None:
            bound_stats = collect_reference_bounds(audio_path.parent, args.fps, exclude_pkl=output_path)
        if bound_stats is None and REFERENCE_BOUNDS_ROOT.exists():
            bound_stats = collect_reference_bounds(REFERENCE_BOUNDS_ROOT, args.fps, exclude_pkl=output_path)
        if bound_stats is None:
            bound_stats = collect_reference_bounds(REPO_ROOT / "data", args.fps, exclude_pkl=output_path)
    if bound_stats is not None:
        features_df, clip_messages = apply_reference_bounds(features_df, bound_stats)

    summary_df, feature_warnings = warn_on_extreme_features(features_df)
    feature_warnings = [*clip_messages, *feature_warnings]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as f:
        pickle.dump(features_df, f, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"saved {output_path}")
    print(f"shape={features_df.shape}")
    print("feature summary:")
    print(summary_df.to_string(float_format=lambda x: f"{x:.6f}"))
    for message in feature_warnings:
        warnings.warn(message)


def main():
    args = parse_args()
    validate_input_path(args.audio_path)

    if args.audio_path.is_file():
        output_path = resolve_output_path(args.audio_path, args.output, args.fps)
        process_audio_path(args.audio_path, args, output_path)
        return

    if args.output is not None and args.output.exists() and not args.output.is_dir():
        raise ValueError(f"--output must be a directory when input is a directory: {args.output}")

    audio_paths = list(iter_audio_paths(args.audio_path))
    if not audio_paths:
        raise ValueError(f"No supported audio files found under: {args.audio_path}")

    failures = []
    for audio_path in audio_paths:
        output_path = resolve_output_path(audio_path, args.output, args.fps, input_root=args.audio_path)
        print(f"processing {audio_path}")
        try:
            process_audio_path(audio_path, args, output_path)
        except Exception as exc:
            failures.append((audio_path, exc))
            print(f"failed {audio_path}: {exc}", file=sys.stderr)

    print(f"processed {len(audio_paths) - len(failures)}/{len(audio_paths)} files")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
