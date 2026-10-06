#!/usr/bin/env python3

import argparse
import os
import contextlib
import pickle
import subprocess
import sys
import time
import shlex
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional



REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
WAV_TO_AUDIO29_SCRIPT = REPO_ROOT / "utils" / "wav_to_audio29_pkl.py"
SYNTHESIZE_SCRIPT = REPO_ROOT / "synthesize.py"
DEFAULT_CHECKPOINT = REPO_ROOT / "pretrained_models" / "dance_LDA-U.ckpt"
DEFAULT_DATASET_ROOT = REPO_ROOT / "data" / "motorica_dance"
SUPPORTED_AUDIO_SUFFIXES = {".wav", ".mp3"}


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
        return len(data)

    def flush(self):
        for stream in self.streams:
            stream.flush()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Batch extract audio29 features from an audio directory and synthesize BVH files."
    )
    parser.add_argument("audio_dir", type=Path, help="Input directory containing .wav/.mp3 files.")
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=DEFAULT_CHECKPOINT,
        help="Model checkpoint used by synthesize.py.",
    )
    parser.add_argument(
        "--dest-dir",
        type=Path,
        default=REPO_ROOT / "results" / "generated" / "audio_dir_to_bvh",
        help="Root directory for generated features, BVH files, and logs.",
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=DEFAULT_DATASET_ROOT,
        help="Dataset root that provides model metadata files required by synthesize.py.",
    )
    parser.add_argument("--fps", type=int, default=30, help="Audio feature frame rate.")
    parser.add_argument("--sample-rate", type=int, default=0, help="Optional audio resample rate.")
    parser.add_argument("--n-fft", type=int, default=2048, help="FFT window size for feature extraction.")
    parser.add_argument(
        "--no-calibration",
        action="store_true",
        help="Disable feature calibration in wav_to_audio29_pkl.py.",
    )
    parser.add_argument("--start", type=int, default=0, help="Start frame for synthesis.")
    parser.add_argument(
        "--end",
        type=int,
        default=None,
        help="End frame for synthesis. Defaults to the extracted feature length.",
    )
    parser.add_argument("--seed", type=int, default=150, help="Random seed for synthesis.")
    parser.add_argument("--limit", type=int, default=0, help="Process at most this many audio files.")
    parser.add_argument("--trim", type=int, default=0, help="Trim frames on each side before BVH export.")
    parser.add_argument("--gpu", type=str, default="cuda:0", help="Device string passed to synthesize.py.")
    parser.add_argument(
        "--gpus",
        type=str,
        default="",
        help="Comma-separated GPU list for multi-process sharding, e.g. cuda:0,cuda:1,cuda:2,cuda:3.",
    )
    parser.add_argument(
        "--num-gpus",
        type=int,
        default=0,
        help="Convenience shorthand for --gpus cuda:0,...,cuda:N-1 when N > 0.",
    )
    parser.add_argument(
        "--synthesize-subprocess",
        action="store_true",
        help="Use a fresh synthesize.py subprocess per file instead of reusing one loaded model.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing them.")
    parser.add_argument("--stop-on-error", action="store_true", help="Stop immediately if one file fails.")
    parser.add_argument("--keep-features", action="store_true", help="Keep extracted feature .pkl files after synthesis.")
    parser.add_argument(
        "--verbose-subprocess",
        action="store_true",
        help="Stream child process output to the terminal in addition to writing log files.",
    )
    parser.add_argument("--shard-index", type=int, default=0, help=argparse.SUPPRESS)
    parser.add_argument("--shard-count", type=int, default=1, help=argparse.SUPPRESS)
    parser.add_argument("--summary-name", type=str, default="summary.tsv", help=argparse.SUPPRESS)
    parser.add_argument("--reference-bounds-dir", type=Path, default=None,
                        help="Explicit reference feature directory; requires --no-calibration.")
    args = parser.parse_args()
    if args.reference_bounds_dir is not None:
        if not args.no_calibration:
            parser.error("--reference-bounds-dir requires --no-calibration")
        args.reference_bounds_dir = args.reference_bounds_dir.expanduser().resolve()
        if not args.reference_bounds_dir.is_dir():
            parser.error("--reference-bounds-dir must be an existing directory")
    return args


def iter_audio_paths(audio_dir: Path):
    for path in sorted(audio_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_AUDIO_SUFFIXES:
            yield path


def run_command(cmd, log_path: Optional[Path] = None, dry_run: bool = False, verbose: bool = False):
    if verbose or dry_run:
        print("running:", " ".join(str(part) for part in cmd))
    if dry_run:
        return 0.0

    started_at = time.perf_counter()
    env = os.environ.copy()
    env.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")

    if log_path is None:
        subprocess.run(cmd, check=True, cwd=REPO_ROOT, env=env)
        return time.perf_counter() - started_at

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"\n[{datetime.now().isoformat(timespec='seconds')}] START {' '.join(str(part) for part in cmd)}\n")
        log_file.flush()
        process = subprocess.Popen(
            cmd,
            cwd=REPO_ROOT,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            text=True,
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            if verbose:
                sys.stdout.write(line)
            log_file.write(line)
        result = process.wait()
        elapsed = time.perf_counter() - started_at
        log_file.write(
            f"[{datetime.now().isoformat(timespec='seconds')}] END returncode={result} elapsed_seconds={elapsed:.3f}\n"
        )
    if result != 0:
        raise subprocess.CalledProcessError(result, cmd)
    return elapsed


def run_logged_callable(description: str, fn, log_path: Optional[Path] = None, dry_run: bool = False, verbose: bool = False):
    if verbose or dry_run:
        print("running:", description)
    if dry_run:
        return 0.0

    started_at = time.perf_counter()
    if log_path is None:
        fn()
        return time.perf_counter() - started_at

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log_file:
        start_line = f"[{datetime.now().isoformat(timespec='seconds')}] START {description}\n"
        if verbose:
            sys.stdout.write(start_line)
        log_file.write(f"\n{start_line}")
        log_file.flush()
        stream = Tee(sys.stdout, log_file) if verbose else log_file
        try:
            with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                fn()
            result = 0
        except Exception:
            result = 1
            traceback.print_exc(file=stream)
            raise
        finally:
            elapsed = time.perf_counter() - started_at
            end_line = (
                f"[{datetime.now().isoformat(timespec='seconds')}] "
                f"END returncode={result} elapsed_seconds={elapsed:.3f}\n"
            )
            if verbose:
                sys.stdout.write(end_line)
            log_file.write(end_line)
    return time.perf_counter() - started_at


def shard_audio_paths(audio_paths, shard_index: int, shard_count: int):
    if shard_count <= 1:
        return audio_paths
    if shard_index < 0 or shard_index >= shard_count:
        raise ValueError(f"Invalid shard index/count: index={shard_index}, count={shard_count}")
    return [path for idx, path in enumerate(audio_paths) if idx % shard_count == shard_index]


def parse_gpu_list(gpus_arg: str):
    return [gpu.strip() for gpu in gpus_arg.split(",") if gpu.strip()]


def resolve_gpus_arg(args):
    if args.gpus:
        return args.gpus
    if args.num_gpus > 0:
        return ",".join(f"cuda:{idx}" for idx in range(args.num_gpus))
    return ""


def append_flag(cmd, flag: str, enabled: bool):
    if enabled:
        cmd.append(flag)


def append_option(cmd, flag: str, value):
    cmd.extend([flag, str(value)])


def launch_sharded_workers(args, audio_dir: Path, checkpoint_path: Path, dataset_root: Path, dest_dir: Path):
    gpus = parse_gpu_list(resolve_gpus_arg(args))
    if len(gpus) <= 1:
        return False

    log_root = dest_dir / "logs"
    shard_log_root = log_root / "shards"
    shard_log_root.mkdir(parents=True, exist_ok=True)

    workers = []
    script_path = Path(__file__).resolve()
    for shard_index, gpu in enumerate(gpus):
        shard_summary_name = f"summary.shard{shard_index}.tsv"
        shard_log_path = shard_log_root / f"shard_{shard_index}_{gpu.replace(':', '_')}.log"
        cmd = [sys.executable, str(script_path), str(audio_dir)]
        append_option(cmd, "--checkpoint", checkpoint_path)
        append_option(cmd, "--dest-dir", dest_dir)
        append_option(cmd, "--dataset-root", dataset_root)
        append_option(cmd, "--fps", args.fps)
        append_option(cmd, "--sample-rate", args.sample_rate)
        append_option(cmd, "--n-fft", args.n_fft)
        append_option(cmd, "--start", args.start)
        if args.end is not None:
            append_option(cmd, "--end", args.end)
        append_option(cmd, "--seed", args.seed)
        append_option(cmd, "--limit", args.limit)
        append_option(cmd, "--trim", args.trim)
        append_option(cmd, "--gpu", gpu)
        append_option(cmd, "--shard-index", shard_index)
        append_option(cmd, "--shard-count", len(gpus))
        append_option(cmd, "--summary-name", shard_summary_name)
        if args.reference_bounds_dir is not None:
            append_option(cmd, "--reference-bounds-dir", args.reference_bounds_dir)
        append_flag(cmd, "--no-calibration", args.no_calibration)
        append_flag(cmd, "--synthesize-subprocess", args.synthesize_subprocess)
        append_flag(cmd, "--dry-run", args.dry_run)
        append_flag(cmd, "--stop-on-error", args.stop_on_error)
        append_flag(cmd, "--keep-features", args.keep_features)
        append_flag(cmd, "--verbose-subprocess", args.verbose_subprocess)

        cmd_text = " ".join(shlex.quote(part) for part in cmd)
        print(f"launch shard {shard_index + 1}/{len(gpus)} on {gpu}: {shard_log_path}")
        if args.verbose_subprocess or args.dry_run:
            print(f"running: {cmd_text}")
        if args.dry_run:
            continue

        env = os.environ.copy()
        env.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")
        shard_log_path.parent.mkdir(parents=True, exist_ok=True)
        log_file = shard_log_path.open("a", encoding="utf-8")
        log_file.write(f"\n[{datetime.now().isoformat(timespec='seconds')}] START {cmd_text}\n")
        log_file.flush()
        stdout = None if args.verbose_subprocess else log_file
        stderr = None if args.verbose_subprocess else subprocess.STDOUT
        process = subprocess.Popen(
            cmd,
            cwd=REPO_ROOT,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            text=True,
            bufsize=1,
        )
        workers.append((shard_index, gpu, process, log_file, shard_log_path, shard_summary_name))

    if args.dry_run:
        return True

    failed = False
    for shard_index, gpu, process, log_file, shard_log_path, shard_summary_name in workers:
        result = process.wait()
        log_file.write(f"[{datetime.now().isoformat(timespec='seconds')}] END returncode={result}\n")
        log_file.close()
        if result == 0:
            print(f"finished shard {shard_index + 1}/{len(gpus)} on {gpu}: {shard_log_path}")
        else:
            failed = True
            print(f"failed shard {shard_index + 1}/{len(gpus)} on {gpu}: {shard_log_path}", file=sys.stderr)

    shard_summary_paths = [log_root / f"summary.shard{idx}.tsv" for idx in range(len(gpus))]
    merged_summary_path = log_root / "summary.tsv"
    header = None
    merged_rows = []
    for shard_summary_path in shard_summary_paths:
        if not shard_summary_path.exists():
            continue
        lines = shard_summary_path.read_text(encoding="utf-8").splitlines()
        if not lines:
            continue
        if header is None:
            header = lines[0]
        merged_rows.extend(lines[1:])
    if header is not None:
        merged_summary_path.write_text("\n".join([header, *merged_rows]) + "\n", encoding="utf-8")
        print(f"summary: {merged_summary_path}")

    if failed:
        raise SystemExit(1)
    return True


def load_feature_frame_count(feature_path: Path) -> int:
    with feature_path.open("rb") as f:
        features_df = pickle.load(f)
    return int(len(features_df))


def load_synthesis_runtime(checkpoint_path: Path, dataset_root: Path):
    from synthesize import load_model_from_checkpoint, synthesize_single

    model = load_model_from_checkpoint(checkpoint_path, dataset_root)
    return {
        "dataset_root": dataset_root,
        "model": model,
        "synthesize_single": synthesize_single,
    }


def synthesize_with_loaded_model(runtime, input_file: Path, start: int, end: int, seed: int, trim: int, dest_dir: Path,
                                 gpu: str, outfile: str):
    dest_dir.mkdir(parents=True, exist_ok=True)
    runtime["synthesize_single"](
        model=runtime["model"],
        data_dir=runtime["dataset_root"],
        input_file=input_file,
        startframe=start,
        endframe=end,
        trim=trim,
        seed=seed,
        dest_dir=dest_dir,
        gpu=gpu,
        render_video=False,
        outfile=outfile,
    )


def write_summary(summary_path: Path, rows):
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "audio_path",
        "extract_status",
        "extract_seconds",
        "synthesize_status",
        "synthesize_seconds",
        "total_seconds",
        "feature_deleted",
        "failure_stage",
        "error",
    ]
    with summary_path.open("w", encoding="utf-8") as f:
        f.write("\t".join(header) + "\n")
        for row in rows:
            values = [str(row.get(key, "")) for key in header]
            f.write("\t".join(values) + "\n")


def main():
    args = parse_args()

    audio_dir = args.audio_dir.expanduser().resolve()
    if not audio_dir.is_dir():
        raise SystemExit(f"Audio directory not found: {audio_dir}")

    checkpoint_path = args.checkpoint.expanduser().resolve()
    if not checkpoint_path.is_file():
        raise SystemExit(f"Checkpoint not found: {checkpoint_path}")

    dataset_root = args.dataset_root.expanduser().resolve()
    if not dataset_root.is_dir():
        raise SystemExit(f"Dataset root not found: {dataset_root}")

    audio_paths = list(iter_audio_paths(audio_dir))
    if args.limit > 0:
        audio_paths = audio_paths[: args.limit]

    dest_dir = args.dest_dir.expanduser().resolve()

    if (args.gpus or args.num_gpus > 0) and args.shard_count == 1:
        launched = launch_sharded_workers(args, audio_dir, checkpoint_path, dataset_root, dest_dir)
        if launched:
            return

    audio_paths = shard_audio_paths(audio_paths, args.shard_index, args.shard_count)
    if not audio_paths:
        print(f"no files assigned to shard {args.shard_index}/{args.shard_count} under: {audio_dir}")
        return

    feature_root = dest_dir / "features"
    bvh_root = dest_dir / "bvh"
    log_root = dest_dir / "logs"
    summary_path = log_root / args.summary_name

    if not args.dry_run:
        feature_root.mkdir(parents=True, exist_ok=True)
        bvh_root.mkdir(parents=True, exist_ok=True)
        log_root.mkdir(parents=True, exist_ok=True)

    failures = []
    summary_rows = []
    skipped = 0
    extract_successes = 0
    synth_successes = 0
    extract_total_seconds = 0.0
    synth_total_seconds = 0.0
    synth_runtime = None

    for audio_path in audio_paths:
        relative_parent = audio_path.parent.relative_to(audio_dir)
        feature_dir = feature_root / relative_parent
        bvh_dir = bvh_root / relative_parent
        log_dir = log_root / relative_parent
        feature_path = feature_dir / f"{audio_path.stem}.audio29_{args.fps}fps.pkl"
        bvh_path = bvh_dir / f"{audio_path.stem}.bvh"
        input_file = feature_path
        outfile = audio_path.stem

        if not args.dry_run:
            feature_dir.mkdir(parents=True, exist_ok=True)
            bvh_dir.mkdir(parents=True, exist_ok=True)
            log_dir.mkdir(parents=True, exist_ok=True)

        if bvh_path.exists():
            skipped += 1
            print(f"skip existing {bvh_path}")
            summary_rows.append(
                {
                    "audio_path": str(audio_path),
                    "extract_status": "skipped",
                    "extract_seconds": "",
                    "synthesize_status": "skipped",
                    "synthesize_seconds": "",
                    "total_seconds": "",
                    "feature_deleted": "false",
                    "failure_stage": "",
                    "error": "",
                }
            )
            continue

        print(f"processing {audio_path}")

        feature_cmd = [
            sys.executable,
            str(WAV_TO_AUDIO29_SCRIPT),
            str(audio_path),
            "--output",
            str(feature_path),
            "--fps",
            str(args.fps),
            "--sample-rate",
            str(args.sample_rate),
            "--n-fft",
            str(args.n_fft),
        ]
        if args.reference_bounds_dir is not None:
            feature_cmd.extend(["--reference-bounds-dir", str(args.reference_bounds_dir)])
        if args.no_calibration:
            feature_cmd.append("--no-calibration")

        row = {
            "audio_path": str(audio_path),
            "extract_status": "pending",
            "extract_seconds": "",
            "synthesize_status": "pending",
            "synthesize_seconds": "",
            "total_seconds": "",
            "feature_deleted": "false",
            "failure_stage": "",
            "error": "",
        }

        try:
            extract_seconds = run_command(feature_cmd, log_dir / f"{audio_path.stem}.extract.log", args.dry_run, args.verbose_subprocess)
            row["extract_status"] = "ok"
            row["extract_seconds"] = f"{extract_seconds:.3f}"
            row["total_seconds"] = f"{extract_seconds:.3f}"
            extract_successes += 1
            extract_total_seconds += extract_seconds

            if args.dry_run:
                row["synthesize_status"] = "dry-run"
                summary_rows.append(row)
                continue

            total_frames = load_feature_frame_count(feature_path)
            end_frame = total_frames if args.end is None else min(args.end, total_frames)
            if end_frame <= args.start:
                raise ValueError(
                    f"Invalid frame range for {audio_path.name}: start={args.start}, end={end_frame}, total_frames={total_frames}"
                )

            synth_log_path = log_dir / f"{audio_path.stem}.synthesize.log"
            if args.synthesize_subprocess:
                synth_cmd = [
                    sys.executable,
                    str(SYNTHESIZE_SCRIPT),
                    f"--checkpoints={checkpoint_path}",
                    f"--data_dirs={dataset_root}",
                    f"--input_files={input_file}",
                    f"--start={args.start}",
                    f"--end={end_frame}",
                    f"--seed={args.seed}",
                    "--postfix=0",
                    f"--trim={args.trim}",
                    f"--dest_dir={bvh_dir}",
                    f"--gpu={args.gpu}",
                    "--video=false",
                    f"--outfile={outfile}",
                ]
                synth_seconds = run_command(synth_cmd, synth_log_path, args.dry_run, args.verbose_subprocess)
            else:
                if synth_runtime is None:
                    print(f"loading model once for shard on {args.gpu}: {checkpoint_path}")
                    synth_runtime = load_synthesis_runtime(checkpoint_path, dataset_root)
                synth_description = (
                    f"in-process synthesize checkpoint={checkpoint_path} "
                    f"input={input_file} start={args.start} end={end_frame} "
                    f"trim={args.trim} dest_dir={bvh_dir} gpu={args.gpu} outfile={outfile}"
                )
                synth_seconds = run_logged_callable(
                    synth_description,
                    lambda: synthesize_with_loaded_model(
                        synth_runtime,
                        input_file,
                        args.start,
                        end_frame,
                        args.seed,
                        args.trim,
                        bvh_dir,
                        args.gpu,
                        outfile,
                    ),
                    synth_log_path,
                    args.dry_run,
                    args.verbose_subprocess,
                )
            row["synthesize_status"] = "ok"
            row["synthesize_seconds"] = f"{synth_seconds:.3f}"
            row["total_seconds"] = f"{extract_seconds + synth_seconds:.3f}"
            synth_successes += 1
            synth_total_seconds += synth_seconds
            if not args.keep_features and feature_path.exists():
                feature_path.unlink()
                row["feature_deleted"] = "true"
            print(f"finished {audio_path}")
        except Exception as exc:
            if row["extract_status"] == "pending":
                row["extract_status"] = "failed"
                row["failure_stage"] = "extract"
            elif row["synthesize_status"] == "pending":
                row["synthesize_status"] = "failed"
                row["failure_stage"] = "synthesize"
            else:
                row["failure_stage"] = "postprocess"
            row["error"] = str(exc).replace("\n", " ")
            failures.append((audio_path, exc))
            print(f"failed {audio_path}: {exc}", file=sys.stderr)
            summary_rows.append(row)
            if args.stop_on_error:
                if not args.dry_run:
                    write_summary(summary_path, summary_rows)
                raise SystemExit(1)
            continue

        summary_rows.append(row)

    processed = len(audio_paths) - len(failures) - skipped
    print(f"processed {processed}/{len(audio_paths)} files")
    print(f"skipped: {skipped}")
    print(f"extract: success={extract_successes}/{len(audio_paths)} total_seconds={extract_total_seconds:.3f}")
    if args.dry_run:
        print("synthesize: dry-run skipped because end frame depends on extracted feature length")
    else:
        print(f"synthesize: success={synth_successes}/{extract_successes} total_seconds={synth_total_seconds:.3f}")
        write_summary(summary_path, summary_rows)
        print(f"summary: {summary_path}")
    print(f"features_root: {feature_root}")
    print(f"bvh_root: {bvh_root}")
    print(f"log_root: {log_root}")

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
