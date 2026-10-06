#!/usr/bin/env python3
"""Validate PRED export bundles and emit one status row per input sample.

A complete RobotMDAR PRED delivery contains ``motion.npz``, ``metadata.txt`` and
``info.txt``.  The exported frames must correspond only to the configured
placeholder instruction, all required arrays must have consistent lengths and
finite values, and the checker exits non-zero when any sample fails.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np


REQUIRED_NPZ_FIELDS = (
    "fps",
    "joint_pos",
    "joint_vel",
    "body_pos_w",
    "body_quat_w",
    "body_lin_vel_w",
    "body_ang_vel_w",
)
FRAME_FIELDS = REQUIRED_NPZ_FIELDS[1:]


def normalize_prompt(text: str) -> str:
    return " ".join(text.strip().lower().split())


def expected_prompt_labels(prompt_path: Path,
                           instructions: List[str]) -> List[str]:
    """Rebuild the metadata labels loop_dar writes for the kept prompt lines."""
    wanted = {normalize_prompt(instruction) for instruction in instructions}
    labels = []
    for line_number, raw_line in enumerate(
            prompt_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if normalize_prompt(line) in wanted:
            labels.append(f"L{line_number}: {line}")
    return labels


def parse_metadata(metadata_path: Path) -> Tuple[List[str], List[str], dict]:
    """Return exported prompt labels, full prompt labels and integer fields."""
    exported: List[str] = []
    full: List[str] = []
    numbers: dict = {}
    section: Optional[str] = None
    for raw_line in metadata_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if line == "Prompt sequence:":
            section = "exported"
            continue
        if line == "Full prompt sequence:":
            section = "full"
            continue
        if line.startswith("- ") and section is not None:
            (exported if section == "exported" else full).append(line[2:])
            continue
        section = None
        for key in ("Total timesteps", "NPZ stand lead-in frames",
                    "NPZ blend-in frames", "NPZ total timesteps"):
            prefix = f"{key}:"
            if line.startswith(prefix):
                numbers[key] = int(line[len(prefix):].strip())
    return exported, full, numbers


def validate_npz(npz_path: Path, expected_frames: int,
                 output_fps: int) -> int:
    """Validate required tracker arrays and return the saved frame count."""
    with np.load(npz_path) as npz:
        missing = [field for field in REQUIRED_NPZ_FIELDS if field not in npz]
        if missing:
            raise ValueError(f"motion.npz missing fields:{','.join(missing)}")

        fps = np.asarray(npz["fps"]).reshape(-1)
        if fps.size != 1 or int(fps[0]) != output_fps:
            raise ValueError(
                f"motion.npz fps {fps.tolist()} differs from expected {output_fps}")

        arrays = {field: np.asarray(npz[field]) for field in FRAME_FIELDS}
        npz_frames = int(arrays["joint_pos"].shape[0])
        if npz_frames != expected_frames:
            raise ValueError(
                f"motion.npz has {npz_frames} frames, expected {expected_frames}")

        if arrays["joint_pos"].ndim != 2 or arrays["joint_pos"].shape[1] != 29:
            raise ValueError(
                f"joint_pos shape {arrays['joint_pos'].shape}, expected ({expected_frames}, 29)")
        if arrays["joint_vel"].shape != arrays["joint_pos"].shape:
            raise ValueError(
                f"joint_vel shape {arrays['joint_vel'].shape} differs from joint_pos")

        body_shapes = {
            "body_pos_w": 3,
            "body_quat_w": 4,
            "body_lin_vel_w": 3,
            "body_ang_vel_w": 3,
        }
        body_count = arrays["body_pos_w"].shape[1] if arrays["body_pos_w"].ndim == 3 else -1
        for field, width in body_shapes.items():
            array = arrays[field]
            if (array.ndim != 3 or array.shape[0] != expected_frames
                    or array.shape[1] != body_count or array.shape[2] != width):
                raise ValueError(f"invalid {field} shape:{array.shape}")

        for field, array in arrays.items():
            if array.shape[0] != expected_frames:
                raise ValueError(
                    f"{field} has {array.shape[0]} frames, expected {expected_frames}")
            if not np.isfinite(array).all():
                raise ValueError(f"{field} contains NaN or Inf")
    return npz_frames


def check_sample(prompt_path: Path, output_dir: Path, instructions: List[str],
                 clip_timesteps: int, output_fps: int) -> str:
    """Return a short detail string, or raise ValueError describing the problem."""
    metadata_path = output_dir / "metadata.txt"
    info_path = output_dir / "info.txt"
    npz_path = output_dir / "motion.npz"
    for path in (metadata_path, info_path, npz_path):
        if not path.is_file():
            raise ValueError(f"missing:{path.name}")
        if path.stat().st_size == 0:
            raise ValueError(f"empty:{path.name}")

    expected = expected_prompt_labels(prompt_path, instructions)
    if not expected:
        raise ValueError("source has no placeholder instruction line")

    exported, full, numbers = parse_metadata(metadata_path)
    if exported != expected:
        raise ValueError(
            f"exported prompts {exported} differ from instruction lines {expected}")

    expected_export_frames = clip_timesteps * len(expected)
    total_timesteps = numbers.get("Total timesteps")
    if total_timesteps != expected_export_frames:
        raise ValueError(
            f"metadata reports {total_timesteps} frames, expected {expected_export_frames}")

    prefix_frames = (numbers.get("NPZ stand lead-in frames", 0) +
                     numbers.get("NPZ blend-in frames", 0))
    expected_npz_frames = expected_export_frames + prefix_frames
    npz_frames = validate_npz(npz_path, expected_npz_frames, output_fps)

    return (f"frames={npz_frames} exported={len(exported)}/"
            f"{len(full) or len(exported)} prompt={exported[0]}")


def read_skipped_relative_paths(path: Optional[Path]) -> set[str]:
    if path is None or not path.is_file():
        return set()
    return {
        line.strip() for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--status-file", required=True, type=Path)
    parser.add_argument("--error-dir", type=Path)
    parser.add_argument("--worker-logs", default="")
    parser.add_argument("--skipped-manifest", type=Path)
    parser.add_argument("--clip-timesteps", required=True, type=int)
    parser.add_argument("--output-fps", required=True, type=int)
    parser.add_argument(
        "--instructions",
        required=True,
        help="'|' separated placeholder instructions that must be exported")
    args = parser.parse_args()

    instructions = [
        part for part in args.instructions.split("|") if part.strip()
    ]
    if not instructions:
        parser.error("--instructions is empty")

    sources = [
        Path(line) for line in args.manifest.read_text(
            encoding="utf-8").splitlines() if line.strip()
    ]
    skipped_relative_paths = read_skipped_relative_paths(args.skipped_manifest)

    if args.error_dir is not None:
        args.error_dir.mkdir(parents=True, exist_ok=True)
    args.status_file.parent.mkdir(parents=True, exist_ok=True)

    success = failed = skipped = 0
    with args.status_file.open("w", encoding="utf-8") as status:
        status.write("status\tsource\tfinal_dir\tdetail\n")
        for source in sources:
            relative_source = source.relative_to(args.source_root)
            sample = relative_source.with_suffix("")
            output_dir = args.output_root / sample
            was_skipped = relative_source.as_posix() in skipped_relative_paths
            try:
                detail = check_sample(source, output_dir, instructions,
                                      args.clip_timesteps, args.output_fps)
            except Exception as exc:  # noqa: BLE001 - reported per sample
                failed += 1
                detail = str(exc).replace("\t", " ").replace("\n", " ")
                status.write(f"failed\t{source}\t{output_dir}\t{detail}\n")
                if args.error_dir is not None:
                    error_name = str(sample).replace("/", "__")
                    (args.error_dir / f"errors_{error_name}.log").write_text(
                        f"source={source}\noutput_dir={output_dir}\n"
                        f"preexisting_complete={was_skipped}\nproblem={detail}\n"
                        f"worker_logs={args.worker_logs}\n",
                        encoding="utf-8")
                continue
            sample_status = "skipped" if was_skipped else "success"
            if was_skipped:
                skipped += 1
            else:
                success += 1
            status.write(
                f"{sample_status}\t{source}\t{output_dir}\t{detail}\n")

    print(
        f"checked={len(sources)} success={success} failed={failed} skipped={skipped}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
