#!/usr/bin/env python3
import argparse
import os
import pathlib
import shutil
import shlex
import subprocess
import sys
import tempfile
import time


HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
DEFAULT_GMR_ROOT = REPO_ROOT.parent / "GMR"
DEFAULT_SRC_DIR = REPO_ROOT / "results" / "generated" / "audio_dir_to_bvh" / "bvh"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / "generated" / "GMR_bvh_to_robot"
DEFAULT_SONIC_SCRIPT = REPO_ROOT / "utils" / "gmr_pkl_to_sonic_folder.py"
DEFAULT_SONIC_XML = REPO_ROOT.parent / "GR00T-WholeBodyControl" / "gear_sonic_deploy/g1/g1_29dof.xml"
DEFAULT_SONIC_BODY_INDEXES = [0, 4, 10, 18, 5, 11, 19, 9, 16, 22, 28, 17, 23, 29]


def infer_output_dir(inputs, src_dir):
    if len(inputs) == 1 and inputs[0].resolve().is_dir():
        base_dir = inputs[0].resolve()
    else:
        base_dir = src_dir.resolve()

    if base_dir.name == "bvh" and base_dir.parent.name == "audio_dir_to_bvh":
        return base_dir.parent.parent / "GMR_bvh_to_robot"

    return base_dir.parent / f"{base_dir.name}_to_robot"


def infer_sonic_output_dir(robot_output_dir):
    return robot_output_dir.parent / f"{robot_output_dir.name}_sonic"


def build_gmr_env(gmr_root):
    env = os.environ.copy()
    pythonpath_parts = [str(REPO_ROOT), str(gmr_root)]
    existing = env.get("PYTHONPATH", "")
    if existing:
        pythonpath_parts.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    return env


def run_command(cmd, env=None):
    print("running:", " ".join(str(part) for part in cmd), flush=True)
    subprocess.run(cmd, check=True, env=env)


def parse_gpu_list(gpus_arg):
    return [gpu.strip() for gpu in gpus_arg.split(",") if gpu.strip()]


def resolve_gpus_arg(args):
    if args.gpus:
        return args.gpus
    if args.num_gpus > 0:
        return ",".join(f"cuda:{idx}" for idx in range(args.num_gpus))
    return ""


def shard_bvh_files(bvh_files, shard_index, shard_count):
    if shard_count <= 1:
        return bvh_files
    if shard_index < 0 or shard_index >= shard_count:
        raise ValueError(f"Invalid shard index/count: index={shard_index}, count={shard_count}")
    return [path for idx, path in enumerate(bvh_files) if idx % shard_count == shard_index]


def append_option(cmd, flag, value):
    cmd.extend([flag, str(value)])


def append_flag(cmd, flag, enabled):
    if enabled:
        cmd.append(flag)


def run_preflight_python(gmr_python, code, *extra_args, env=None):
    result = subprocess.run(
        [str(gmr_python), "-c", code, *extra_args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        env=env,
    )
    if result.returncode == 0:
        return

    detail_parts = []
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    if stdout:
        detail_parts.append(stdout)
    if stderr:
        detail_parts.append(stderr)
    detail = "\n".join(detail_parts) if detail_parts else f"exit code {result.returncode}"
    raise SystemExit(detail)


def preflight_or_die(args, gmr_python, requested_devices):
    gmr_env = build_gmr_env(args.gmr_root)
    if args.position_backend == "pymo":
        try:
            run_preflight_python(
                gmr_python,
                "from pymo.parsers import BVHParser",
                env=gmr_env,
            )
        except SystemExit as exc:
            raise SystemExit(
                "Preflight failed: missing dependency `pymo` in gmr environment.\n"
                f"gmr python: {gmr_python}\n"
                f"{exc}"
            ) from None

    cuda_devices = [device for device in requested_devices if device.startswith("cuda")]
    if not cuda_devices:
        return

    try:
        run_preflight_python(
            gmr_python,
            (
                "import sys, torch\n"
                "targets = sys.argv[1:]\n"
                "if not torch.cuda.is_available():\n"
                "    raise SystemExit('CUDA is not available in the gmr environment')\n"
                "count = torch.cuda.device_count()\n"
                "bad = []\n"
                "for target in targets:\n"
                "    index = 0 if target == 'cuda' else int(target.split(':', 1)[1])\n"
                "    if index < 0 or index >= count:\n"
                "        bad.append(target)\n"
                "print(f'cuda_device_count={count}')\n"
                "if bad:\n"
                "    raise SystemExit('Requested CUDA devices unavailable: ' + ', '.join(bad))\n"
            ),
            *cuda_devices,
            env=gmr_env,
        )
    except SystemExit as exc:
        raise SystemExit(
            "Preflight failed: CUDA is not usable from the gmr environment.\n"
            f"requested devices: {', '.join(cuda_devices)}\n"
            f"gmr python: {gmr_python}\n"
            f"{exc}"
        ) from None


def launch_sharded_workers(args, output_dir, bvh_files):
    gpus = parse_gpu_list(resolve_gpus_arg(args))
    if len(gpus) <= 1:
        return False

    log_root = output_dir / "logs"
    shard_log_root = log_root / "shards"
    shard_log_root.mkdir(parents=True, exist_ok=True)

    workers = []
    script_path = pathlib.Path(__file__).resolve()
    print(f"launching {len(gpus)} shard workers", flush=True)
    print(f"shard logs: {shard_log_root}", flush=True)
    for shard_index, gpu in enumerate(gpus):
        shard_files = shard_bvh_files(bvh_files, shard_index, len(gpus))
        if not shard_files:
            continue

        shard_log_path = shard_log_root / f"shard_{shard_index}_{gpu.replace(':', '_')}.log"
        cmd = [sys.executable, str(script_path), *[str(path) for path in shard_files]]
        append_option(cmd, "--output-dir", output_dir)
        append_option(cmd, "--gmr-root", args.gmr_root)
        append_option(cmd, "--gmr-python", args.gmr_python)
        append_option(cmd, "--robot", args.robot)
        append_option(cmd, "--position-backend", args.position_backend)
        append_option(cmd, "--gender", args.gender)
        append_option(cmd, "--device", gpu)
        append_option(cmd, "--num-iters-stage1", args.num_iters_stage1)
        append_option(cmd, "--num-iters-stage2", args.num_iters_stage2)
        append_flag(cmd, "--overwrite", args.overwrite)
        append_flag(cmd, "--keep-temp", args.keep_temp)
        append_flag(cmd, "--skip-sonic", True)
        append_option(cmd, "--sonic-script", args.sonic_script)
        append_option(cmd, "--sonic-python", args.sonic_python)
        append_option(cmd, "--sonic-output-dir", args.sonic_output_dir)
        append_flag(cmd, "--skip-existing-sonic", args.skip_existing_sonic)
        append_option(cmd, "--sonic-xml", args.sonic_xml)
        cmd.extend(["--body-indexes", *[str(index) for index in args.body_indexes]])
        append_option(cmd, "--target-fps", args.target_fps)
        append_flag(cmd, "--no-ground-adjust", args.no_ground_adjust)
        append_option(cmd, "--ground-clearance", args.ground_clearance)
        append_option(cmd, "--smooth-window", args.smooth_window)
        append_option(cmd, "--height-correct-window", args.height_correct_window)
        append_option(cmd, "--velocity-sigma", args.velocity_sigma)

        cmd_text = " ".join(shlex.quote(part) for part in cmd)
        print(f"launch shard {shard_index + 1}/{len(gpus)} on {gpu}: {shard_log_path}")
        log_file = shard_log_path.open("a", encoding="utf-8")
        log_file.write(f"\n[{time.strftime('%Y-%m-%dT%H:%M:%S')}] START {cmd_text}\n")
        log_file.flush()
        env = os.environ.copy()
        process = subprocess.Popen(
            cmd,
            cwd=REPO_ROOT,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
        )
        workers.append((shard_index, gpu, process, log_file, shard_log_path))

    failed = False
    for shard_index, gpu, process, log_file, shard_log_path in workers:
        result = process.wait()
        log_file.write(f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] END returncode={result}\n")
        log_file.close()
        if result == 0:
            print(f"finished shard {shard_index + 1}/{len(gpus)} on {gpu}: {shard_log_path}")
        else:
            failed = True
            print(f"failed shard {shard_index + 1}/{len(gpus)} on {gpu}: {shard_log_path}", file=sys.stderr)

    if failed:
        raise SystemExit(1)

    if not args.skip_sonic:
        sonic_output_dir = (
            args.sonic_output_dir.expanduser().resolve()
            if args.sonic_output_dir is not None
            else infer_sonic_output_dir(output_dir)
        )
        sonic_cmd = [
            str(args.sonic_python.expanduser().resolve()),
            str(args.sonic_script.expanduser().resolve()),
            str(output_dir),
            "--output-dir",
            str(sonic_output_dir),
            "--sonic-xml",
            str(args.sonic_xml.expanduser().resolve()),
            "--target-fps",
            str(args.target_fps),
            "--ground-clearance",
            str(args.ground_clearance),
            "--smooth-window",
            str(args.smooth_window),
            "--height-correct-window",
            str(args.height_correct_window),
            "--velocity-sigma",
            str(args.velocity_sigma),
            "--body-indexes",
            *[str(index) for index in args.body_indexes],
        ]
        if args.skip_existing_sonic:
            sonic_cmd.append("--skip-existing")
        if args.no_ground_adjust:
            sonic_cmd.append("--no-ground-adjust")

        sonic_started_at = time.perf_counter()
        run_command(sonic_cmd)
        sonic_seconds = time.perf_counter() - sonic_started_at
        print(f"sonic output dir: {sonic_output_dir}")

    return True


def collect_bvh_files(inputs, src_dir, pattern):
    bvh_files = []
    if inputs:
        for raw_path in inputs:
            path = raw_path.resolve()
            if path.is_file():
                if path.suffix.lower() != ".bvh":
                    raise ValueError(f"Input file is not a BVH file: {path}")
                bvh_files.append(path)
            elif path.is_dir():
                bvh_files.extend(sorted(path.glob(pattern)))
            else:
                raise FileNotFoundError(f"Input path does not exist: {raw_path}")
    else:
        src_dir = src_dir.resolve()
        if not src_dir.is_dir():
            raise FileNotFoundError(f"Source directory does not exist: {src_dir}")
        bvh_files.extend(sorted(src_dir.glob(pattern)))

    return sorted(dict.fromkeys(path.resolve() for path in bvh_files))


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Batch convert BVH to temporary SMPL-X, retarget to robot PKL, and export SONIC folders."
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        type=pathlib.Path,
        help="Optional BVH files or directories. If omitted, --src-dir is scanned.",
    )
    parser.add_argument("--src-dir", type=pathlib.Path, default=DEFAULT_SRC_DIR)
    parser.add_argument("--pattern", default="*.bvh")
    parser.add_argument("--gmr-root", type=pathlib.Path, default=DEFAULT_GMR_ROOT,
                        help="GMR checkout root (default: sibling GMR directory).")
    parser.add_argument("--gmr-python", type=pathlib.Path, default=pathlib.Path(sys.executable),
                        help="Path to Python with GMR dependencies installed (default: current Python).")
    parser.add_argument("--robot", default="unitree_g1")
    parser.add_argument(
        "--output-dir",
        type=pathlib.Path,
        default=None,
        help="Output directory for retargeted robot PKL files. Defaults to a path inferred from the input directory.",
    )
    parser.add_argument("--position-backend", default="pymo", choices=["custom", "pymo"])
    parser.add_argument("--gender", default="neutral", choices=["neutral", "male", "female"])
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--gpus", default="", help="Comma-separated GPU list for multi-process sharding, e.g. cuda:0,cuda:1,cuda:2,cuda:3.")
    parser.add_argument("--num-gpus", type=int, default=0, help="Convenience shorthand for --gpus cuda:0,...,cuda:N-1 when N > 0.")
    parser.add_argument("--num-iters-stage1", type=int, default=60)
    parser.add_argument("--num-iters-stage2", type=int, default=180)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--keep-temp", action="store_true")
    parser.add_argument("--skip-sonic", action="store_true")
    parser.add_argument("--sonic-script", type=pathlib.Path, default=DEFAULT_SONIC_SCRIPT)
    parser.add_argument("--sonic-python", type=pathlib.Path, default=None,
                        help="SONIC export Python (default: resolved --gmr-python).")
    parser.add_argument("--sonic-output-dir", type=pathlib.Path, default=None)
    parser.add_argument("--skip-existing-sonic", action="store_true")
    parser.add_argument("--sonic-xml", type=pathlib.Path, default=DEFAULT_SONIC_XML)
    parser.add_argument("--body-indexes", type=int, nargs="+", default=DEFAULT_SONIC_BODY_INDEXES)
    parser.add_argument("--target-fps", type=float, default=50.0)
    parser.add_argument("--no-ground-adjust", action="store_true")
    parser.add_argument("--ground-clearance", type=float, default=0.01)
    parser.add_argument("--smooth-window", type=int, default=0)
    parser.add_argument("--height-correct-window", type=int, default=9)
    parser.add_argument("--velocity-sigma", type=float, default=1.5)
    return parser


def main():
    args = build_arg_parser().parse_args()

    args.gmr_root = args.gmr_root.expanduser().resolve()
    args.gmr_python = args.gmr_python.expanduser().resolve()
    args.sonic_python = (args.sonic_python or args.gmr_python).expanduser().resolve()
    if not args.gmr_root.is_dir():
        raise FileNotFoundError(f"GMR checkout not found: {args.gmr_root}. Set --gmr-root.")
    convert_script = args.gmr_root / "scripts" / "convert_bvh_to_smplx.py"
    retarget_script = args.gmr_root / "scripts" / "smplx_to_robot.py"
    sonic_script = args.sonic_script.expanduser().resolve()
    sonic_python = args.sonic_python.expanduser().resolve()
    gmr_python = args.gmr_python
    if not convert_script.is_file():
        raise FileNotFoundError(f"Missing converter script: {convert_script}")
    if not retarget_script.is_file():
        raise FileNotFoundError(f"Missing retarget script: {retarget_script}")
    if not gmr_python.is_file():
        raise FileNotFoundError(f"Missing GMR Python: {gmr_python}. Set --gmr-python.")
    if not os.access(gmr_python, os.X_OK):
        raise PermissionError(f"GMR Python is not executable: {gmr_python}")
    if not args.skip_sonic and not sonic_python.is_file():
        raise FileNotFoundError(f"Missing sonic python: {sonic_python}")
    if not args.skip_sonic and not sonic_script.is_file():
        raise FileNotFoundError(f"Missing SONIC converter script: {sonic_script}")

    bvh_files = collect_bvh_files(args.inputs, args.src_dir, args.pattern)
    if args.limit > 0:
        bvh_files = bvh_files[: args.limit]
    if not bvh_files:
        raise FileNotFoundError("No BVH files matched the requested inputs.")

    output_dir = args.output_dir.resolve() if args.output_dir else infer_output_dir(args.inputs, args.src_dir)
    requested_devices = parse_gpu_list(resolve_gpus_arg(args))
    if not requested_devices:
        requested_devices = [args.device]

    print(f"inputs: {len(bvh_files)} BVH files", flush=True)
    print(f"output dir: {output_dir}", flush=True)
    print(f"requested devices: {', '.join(requested_devices)}", flush=True)
    if not args.skip_sonic:
        print(f"sonic python: {sonic_python}", flush=True)
    preflight_or_die(args, gmr_python, requested_devices)

    if (args.gpus or args.num_gpus > 0) and launch_sharded_workers(args, output_dir, bvh_files):
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"resolved output dir: {output_dir}")
    gmr_env = build_gmr_env(args.gmr_root)

    failures = []
    converted = 0
    skipped = 0
    gmr_started_at = time.perf_counter()
    for index, bvh_file in enumerate(bvh_files, start=1):
        stem = bvh_file.stem
        save_path = output_dir / f"{stem}_{args.robot}_headless.pkl"
        if save_path.exists() and not args.overwrite:
            print(f"[{index}/{len(bvh_files)}] skip existing: {save_path}")
            skipped += 1
            continue

        print(f"[{index}/{len(bvh_files)}] processing: {bvh_file}")

        tmp_root_obj = None
        if args.keep_temp:
            tmp_root = output_dir / "_tmp_smplx" / stem
            tmp_root.mkdir(parents=True, exist_ok=True)
        else:
            tmp_root_obj = tempfile.TemporaryDirectory(prefix=f"{stem}_", dir=str(output_dir))
            tmp_root = pathlib.Path(tmp_root_obj.name)

        tmp_npz = tmp_root / f"{stem}_smplx_pymo_hiiter.npz"
        tmp_map = tmp_root / f"{stem}_bvh_to_smplx_map_pymo_hiiter.json"

        try:
            run_command(
                [
                    str(gmr_python),
                    str(convert_script),
                    "--bvh",
                    str(bvh_file),
                    "--output",
                    str(tmp_npz),
                    "--dump-map-json",
                    str(tmp_map),
                    "--position-backend",
                    args.position_backend,
                    "--gender",
                    args.gender,
                    "--device",
                    args.device,
                    "--num-iters-stage1",
                    str(args.num_iters_stage1),
                    "--num-iters-stage2",
                    str(args.num_iters_stage2),
                ],
                env=gmr_env,
            )

            run_command(
                [
                    str(gmr_python),
                    str(retarget_script),
                    "--smplx_file",
                    str(tmp_npz),
                    "--robot",
                    args.robot,
                    "--save_path",
                    str(save_path),
                    "--headless",
                ],
                env=gmr_env,
            )
            converted += 1
        except subprocess.CalledProcessError as exc:
            failures.append((str(bvh_file), exc.returncode))
            print(f"failed: {bvh_file} (exit code {exc.returncode})", file=sys.stderr)
        finally:
            if tmp_root_obj is not None:
                tmp_root_obj.cleanup()
            elif not args.keep_temp and tmp_root.exists():
                shutil.rmtree(tmp_root, ignore_errors=True)

    gmr_seconds = time.perf_counter() - gmr_started_at

    sonic_seconds = 0.0
    if not args.skip_sonic:
        sonic_output_dir = (
            args.sonic_output_dir.expanduser().resolve()
            if args.sonic_output_dir is not None
            else infer_sonic_output_dir(output_dir)
        )
        sonic_cmd = [
            str(sonic_python),
            str(sonic_script),
            str(output_dir),
            "--output-dir",
            str(sonic_output_dir),
            "--sonic-xml",
            str(args.sonic_xml.expanduser().resolve()),
            "--target-fps",
            str(args.target_fps),
            "--ground-clearance",
            str(args.ground_clearance),
            "--smooth-window",
            str(args.smooth_window),
            "--height-correct-window",
            str(args.height_correct_window),
            "--velocity-sigma",
            str(args.velocity_sigma),
            "--body-indexes",
            *[str(index) for index in args.body_indexes],
        ]
        if args.skip_existing_sonic:
            sonic_cmd.append("--skip-existing")
        if args.no_ground_adjust:
            sonic_cmd.append("--no-ground-adjust")

        sonic_started_at = time.perf_counter()
        run_command(sonic_cmd, env=gmr_env)
        sonic_seconds = time.perf_counter() - sonic_started_at
        print(f"sonic output dir: {sonic_output_dir}")

    total_seconds = gmr_seconds + sonic_seconds
    failed = len(failures)
    total = len(bvh_files)

    print("stage_timing_seconds:")
    print(f"  gmr={gmr_seconds:.3f}")
    print(f"  sonic={sonic_seconds:.3f}")
    print(f"  total={total_seconds:.3f}")
    print("summary:")
    print(f"  total={total}")
    print(f"  converted={converted}")
    print(f"  skipped={skipped}")
    print(f"  failed={failed}")
    print(f"output dir: {output_dir}")

    if failures:
        print("failures:", file=sys.stderr)
        for path_item, code in failures:
            print(f"  {path_item} -> exit code {code}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
