#!/usr/bin/env python3

import argparse
import importlib.machinery
import importlib.util
import pickle
import sys
import types
from pathlib import Path

import numpy as np
import torch
from scipy.ndimage import gaussian_filter1d


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = REPO_ROOT / "results" / "generated" / "GMR_bvh_to_robot"
DEFAULT_SONIC_XML = REPO_ROOT.parent / "GR00T-WholeBodyControl" / "gear_sonic_deploy/g1/g1_29dof.xml"
DEFAULT_BODY_INDEXES = [0, 4, 10, 18, 5, 11, 19, 9, 16, 22, 28, 17, 23, 29]

# SONIC stores joint positions in IsaacLab order and later remaps them back to
# MuJoCo order when generating robot targets.
ISAACLAB_TO_MUJOCO = np.array(
    [0, 3, 6, 9, 13, 17, 1, 4, 7, 10, 14, 18, 2, 5, 8, 11, 15, 19, 21, 23, 25, 27, 12, 16, 20, 22, 24, 26, 28],
    dtype=np.int64,
)
MUJOCO_TO_ISAACLAB = np.array(
    [0, 6, 12, 1, 7, 13, 2, 8, 14, 3, 9, 15, 22, 4, 10, 16, 23, 5, 11, 17, 24, 18, 25, 19, 26, 20, 27, 21, 28],
    dtype=np.int64,
)


def _load_kinematics_model_without_gmr_init():
    package_name = "general_motion_retargeting"
    package_dir = None

    package_spec = importlib.util.find_spec(package_name)
    if package_spec is not None and package_spec.submodule_search_locations:
        package_dir = Path(next(iter(package_spec.submodule_search_locations)))
    else:
        fallback_dir = (REPO_ROOT.parent / "GMR") / package_name
        if fallback_dir.exists():
            package_dir = fallback_dir

    if package_dir is None:
        raise ModuleNotFoundError(
            "Could not locate the general_motion_retargeting package for fallback import."
        )

    if package_name not in sys.modules:
        package_module = types.ModuleType(package_name)
        package_module.__path__ = [str(package_dir)]
        package_module.__package__ = package_name
        package_module.__spec__ = importlib.machinery.ModuleSpec(
            package_name,
            loader=None,
            is_package=True,
        )
        package_module.__spec__.submodule_search_locations = [str(package_dir)]
        sys.modules[package_name] = package_module

    for module_name in ("torch_utils", "kinematics_model"):
        full_name = f"{package_name}.{module_name}"
        if full_name in sys.modules:
            continue

        module_path = package_dir / f"{module_name}.py"
        module_spec = importlib.util.spec_from_file_location(full_name, module_path)
        if module_spec is None or module_spec.loader is None:
            raise ImportError(f"Could not load fallback module: {module_path}")

        module = importlib.util.module_from_spec(module_spec)
        sys.modules[full_name] = module
        module_spec.loader.exec_module(module)

    return sys.modules[f"{package_name}.kinematics_model"].KinematicsModel


try:
    from general_motion_retargeting.kinematics_model import KinematicsModel
except ModuleNotFoundError:
    KinematicsModel = _load_kinematics_model_without_gmr_init()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert GMR robot motion PKL file(s) into SONIC-style folder(s)."
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to a source GMR robot trajectory pickle or a directory containing pickles.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Output folder. For a single input PKL this is the motion folder to create. "
            "For a directory input this becomes the batch output root."
        ),
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default="*.pkl",
        help="Glob pattern used when input points to a directory.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip an output motion folder if it already contains metadata.txt.",
    )
    parser.add_argument(
        "--sonic-xml",
        type=Path,
        default=DEFAULT_SONIC_XML,
        help="SONIC MuJoCo XML used to rebuild body poses in SONIC's convention.",
    )
    parser.add_argument(
        "--body-indexes",
        type=int,
        nargs="+",
        default=DEFAULT_BODY_INDEXES,
        help="SONIC body indexes to export into body CSV files.",
    )
    parser.add_argument(
        "--target-fps",
        type=float,
        default=50.0,
        help="Export fps. SONIC normally runs reference motion at 50 Hz.",
    )
    parser.add_argument(
        "--no-ground-adjust",
        action="store_true",
        help="Disable the ground-alignment offset that shifts the full motion onto the floor.",
    )
    parser.add_argument(
        "--ground-clearance",
        type=float,
        default=0.01,
        help="Target minimum z height for the exported body subset after ground alignment.",
    )
    parser.add_argument(
        "--smooth-window",
        type=int,
        default=0,
        help="Optional odd moving-average window applied after resampling. Set <= 1 to disable.",
    )
    parser.add_argument(
        "--height-correct-window",
        type=int,
        default=9,
        help="Odd smoothing window for per-frame height correction. Set <= 1 to use raw per-frame correction.",
    )
    parser.add_argument(
        "--velocity-sigma",
        type=float,
        default=1.5,
        help="Gaussian sigma applied to exported velocity tracks. Set <= 0 to disable.",
    )
    return parser.parse_args()


def load_gmr_motion(path):
    with path.open("rb") as f:
        motion_data = pickle.load(f)

    required_keys = ("fps", "root_pos", "root_rot", "dof_pos")
    missing = [key for key in required_keys if key not in motion_data]
    if missing:
        raise KeyError(f"Missing required keys in {path}: {missing}")

    fps = float(motion_data["fps"])
    root_pos = np.asarray(motion_data["root_pos"], dtype=np.float32)
    root_rot_xyzw = np.asarray(motion_data["root_rot"], dtype=np.float32)
    dof_pos_mujoco = np.asarray(motion_data["dof_pos"], dtype=np.float32)

    if root_pos.ndim != 2 or root_pos.shape[1] != 3:
        raise ValueError(f"root_pos must have shape [T, 3], got {root_pos.shape}")
    if root_rot_xyzw.ndim != 2 or root_rot_xyzw.shape[1] != 4:
        raise ValueError(f"root_rot must have shape [T, 4], got {root_rot_xyzw.shape}")
    if dof_pos_mujoco.ndim != 2 or dof_pos_mujoco.shape[1] != 29:
        raise ValueError(f"dof_pos must have shape [T, 29], got {dof_pos_mujoco.shape}")
    if not (root_pos.shape[0] == root_rot_xyzw.shape[0] == dof_pos_mujoco.shape[0]):
        raise ValueError(
            "root_pos, root_rot, and dof_pos must have the same frame count, "
            f"got {root_pos.shape[0]}, {root_rot_xyzw.shape[0]}, {dof_pos_mujoco.shape[0]}"
        )

    return fps, root_pos, root_rot_xyzw, dof_pos_mujoco


def ensure_quat_continuity_xyzw(quat_xyzw):
    quat_xyzw = quat_xyzw.copy()
    for idx in range(1, quat_xyzw.shape[0]):
        dots = np.sum(quat_xyzw[idx - 1] * quat_xyzw[idx], axis=-1, keepdims=True)
        quat_xyzw[idx] = np.where(dots < 0.0, -quat_xyzw[idx], quat_xyzw[idx])
    return quat_xyzw


def normalize_quat_xyzw(quat_xyzw):
    norms = np.linalg.norm(quat_xyzw, axis=-1, keepdims=True)
    norms = np.clip(norms, 1e-8, None)
    return (quat_xyzw / norms).astype(np.float32)


def quat_conjugate_xyzw(quat_xyzw):
    conj = quat_xyzw.copy()
    conj[..., :3] *= -1.0
    return conj


def quat_mul_xyzw(a_xyzw, b_xyzw):
    ax, ay, az, aw = np.moveaxis(a_xyzw, -1, 0)
    bx, by, bz, bw = np.moveaxis(b_xyzw, -1, 0)
    return np.stack(
        [
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz,
        ],
        axis=-1,
    )


def quat_to_rotvec_xyzw(quat_xyzw):
    quat_xyzw = normalize_quat_xyzw(quat_xyzw)
    xyz = quat_xyzw[..., :3]
    w = np.clip(quat_xyzw[..., 3], -1.0, 1.0)
    xyz_norm = np.linalg.norm(xyz, axis=-1, keepdims=True)

    angle = 2.0 * np.arctan2(xyz_norm[..., 0], w)
    angle = (angle + np.pi) % (2.0 * np.pi) - np.pi

    axis = np.zeros_like(xyz)
    nonzero = xyz_norm[..., 0] > 1e-8
    axis[nonzero] = xyz[nonzero] / xyz_norm[nonzero]
    return axis * angle[..., None]


def angular_velocity_from_quats_xyzw(quat_xyzw, dt):
    quat_xyzw = ensure_quat_continuity_xyzw(quat_xyzw)
    quat_xyzw = normalize_quat_xyzw(quat_xyzw)
    if quat_xyzw.shape[0] == 1:
        return np.zeros(quat_xyzw.shape[:-1] + (3,), dtype=np.float32)

    ang_vel = np.zeros(quat_xyzw.shape[:-1] + (3,), dtype=np.float32)
    rel_forward = quat_mul_xyzw(quat_xyzw[1], quat_conjugate_xyzw(quat_xyzw[0]))
    ang_vel[0] = (quat_to_rotvec_xyzw(rel_forward) / dt).astype(np.float32)

    rel_backward = quat_mul_xyzw(quat_xyzw[-1], quat_conjugate_xyzw(quat_xyzw[-2]))
    ang_vel[-1] = (quat_to_rotvec_xyzw(rel_backward) / dt).astype(np.float32)

    if quat_xyzw.shape[0] > 2:
        rel_center = quat_mul_xyzw(quat_xyzw[2:], quat_conjugate_xyzw(quat_xyzw[:-2]))
        ang_vel[1:-1] = (quat_to_rotvec_xyzw(rel_center) / (2.0 * dt)).astype(np.float32)
    return ang_vel


def finite_difference(values, dt):
    if values.shape[0] == 1:
        return np.zeros_like(values, dtype=np.float32)
    return np.gradient(values, dt, axis=0).astype(np.float32)


def smooth_array(values, window):
    if window is None or window <= 1:
        return values
    if window % 2 == 0:
        raise ValueError("smooth_window must be an odd integer")
    if values.shape[0] < 2:
        return values

    pad = window // 2
    flat = values.reshape(values.shape[0], -1)
    padded = np.pad(flat, ((pad, pad), (0, 0)), mode="edge")
    kernel = np.ones(window, dtype=np.float32) / float(window)
    smoothed = np.empty_like(flat)
    for col in range(flat.shape[1]):
        smoothed[:, col] = np.convolve(padded[:, col], kernel, mode="valid")
    return smoothed.reshape(values.shape).astype(np.float32)


def smooth_array_gaussian(values, sigma):
    if sigma is None or sigma <= 0:
        return values.astype(np.float32)
    return gaussian_filter1d(values, sigma=float(sigma), axis=0, mode="nearest").astype(np.float32)


def smooth_quaternions_xyzw(quat_xyzw, window):
    if window is None or window <= 1:
        return normalize_quat_xyzw(quat_xyzw)
    quat_xyzw = ensure_quat_continuity_xyzw(quat_xyzw)
    smoothed = smooth_array(quat_xyzw, window)
    return normalize_quat_xyzw(smoothed)


def build_target_times(num_frames, src_fps, target_fps):
    if num_frames <= 1 or target_fps is None or target_fps <= 0:
        return None
    if abs(float(src_fps) - float(target_fps)) < 1e-6:
        return None

    duration = (num_frames - 1) / float(src_fps)
    target_times = np.arange(0.0, duration + 1e-12, 1.0 / float(target_fps), dtype=np.float64)
    if target_times.size == 0:
        target_times = np.array([0.0], dtype=np.float64)
    return target_times


def resample_linear(values, src_fps, target_fps):
    target_times = build_target_times(values.shape[0], src_fps, target_fps)
    if target_times is None:
        return values.astype(np.float32), float(src_fps)

    source_times = np.arange(values.shape[0], dtype=np.float64) / float(src_fps)
    flat = values.reshape(values.shape[0], -1)
    resampled = np.empty((target_times.shape[0], flat.shape[1]), dtype=np.float32)
    for col in range(flat.shape[1]):
        resampled[:, col] = np.interp(target_times, source_times, flat[:, col]).astype(np.float32)
    return resampled.reshape((target_times.shape[0],) + values.shape[1:]), float(target_fps)


def quat_slerp_xyzw(q0_xyzw, q1_xyzw, alpha):
    q0_xyzw = normalize_quat_xyzw(q0_xyzw)
    q1_xyzw = normalize_quat_xyzw(q1_xyzw)

    dots = np.sum(q0_xyzw * q1_xyzw, axis=-1, keepdims=True)
    q1_xyzw = np.where(dots < 0.0, -q1_xyzw, q1_xyzw)
    dots = np.clip(np.sum(q0_xyzw * q1_xyzw, axis=-1, keepdims=True), -1.0, 1.0)

    alpha = np.asarray(alpha, dtype=np.float32)[..., None]
    linear_mask = np.abs(dots) > 0.9995

    theta_0 = np.arccos(dots)
    sin_theta_0 = np.sin(theta_0)
    theta = theta_0 * alpha
    sin_theta = np.sin(theta)

    s0 = np.sin(theta_0 - theta) / np.clip(sin_theta_0, 1e-8, None)
    s1 = sin_theta / np.clip(sin_theta_0, 1e-8, None)
    slerped = s0 * q0_xyzw + s1 * q1_xyzw
    lerped = (1.0 - alpha) * q0_xyzw + alpha * q1_xyzw
    return normalize_quat_xyzw(np.where(linear_mask, lerped, slerped))


def resample_quaternions_xyzw(quat_xyzw, src_fps, target_fps):
    target_times = build_target_times(quat_xyzw.shape[0], src_fps, target_fps)
    if target_times is None:
        return normalize_quat_xyzw(quat_xyzw), float(src_fps)

    quat_xyzw = ensure_quat_continuity_xyzw(quat_xyzw)
    quat_xyzw = normalize_quat_xyzw(quat_xyzw)
    source_times = np.arange(quat_xyzw.shape[0], dtype=np.float64) / float(src_fps)

    upper = np.searchsorted(source_times, target_times, side="right")
    upper = np.clip(upper, 1, quat_xyzw.shape[0] - 1)
    lower = upper - 1

    t0 = source_times[lower]
    t1 = source_times[upper]
    alpha = (target_times - t0) / np.clip(t1 - t0, 1e-8, None)
    alpha = alpha.astype(np.float32)
    alpha[t1 <= t0] = 0.0

    return quat_slerp_xyzw(quat_xyzw[lower], quat_xyzw[upper], alpha), float(target_fps)


def resample_motion(root_pos, root_rot_xyzw, dof_pos_mujoco, src_fps, target_fps):
    root_pos, export_fps = resample_linear(root_pos, src_fps, target_fps)
    root_rot_xyzw, export_fps_quat = resample_quaternions_xyzw(root_rot_xyzw, src_fps, target_fps)
    dof_pos_mujoco, export_fps_dof = resample_linear(dof_pos_mujoco, src_fps, target_fps)
    if not (abs(export_fps - export_fps_quat) < 1e-6 and abs(export_fps - export_fps_dof) < 1e-6):
        raise RuntimeError("Internal resampling fps mismatch")
    return root_pos, root_rot_xyzw, dof_pos_mujoco, export_fps


def compute_per_frame_ground_offset(body_pos_t, storage_indexes, target_clearance, smooth_window):
    selected_body_pos_t = body_pos_t[:, storage_indexes, :]
    min_selected_z = selected_body_pos_t[..., 2].amin(dim=1).cpu().numpy().astype(np.float32)
    raw_offsets = min_selected_z - float(target_clearance)
    offsets = raw_offsets
    if smooth_window is not None and smooth_window > 1:
        offsets = smooth_array(offsets[:, None], smooth_window).reshape(-1)
    offsets = np.minimum(offsets, raw_offsets)
    return offsets.astype(np.float32)


def flatten_last_dims(array):
    return array.reshape(array.shape[0], -1)


def write_csv(path, array, header):
    np.savetxt(
        path,
        array,
        delimiter=",",
        header=",".join(header),
        comments="",
        fmt="%.6f",
    )


def build_body_vector_header(num_bodies, suffixes):
    header = []
    for body_idx in range(num_bodies):
        for suffix in suffixes:
            header.append(f"body_{body_idx}_{suffix}")
    return header


def format_sample(array):
    flat = np.asarray(array).reshape(-1)
    return np.array2string(flat[:5], precision=8, separator=" ")


def build_info_text(name, arrays):
    lines = [
        f"Motion Information: {name}",
        "=" * 50,
        "",
    ]
    ordered_names = [
        "joint_pos",
        "joint_vel",
        "body_pos_w",
        "body_quat_w",
        "body_lin_vel_w",
        "body_ang_vel_w",
        "_body_indexes",
        "time_step_total",
    ]
    for key in ordered_names:
        value_np = np.asarray(arrays[key])
        lines.append(f"{key}:")
        lines.append(f"  Shape: {value_np.shape}")
        lines.append(f"  Dtype: {value_np.dtype}")
        lines.append(f"  Range: [{value_np.min():.3f}, {value_np.max():.3f}]")
        lines.append(f"  Sample: {format_sample(value_np)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_metadata_text(name, arrays):
    lines = [
        f"Metadata for: {name}",
        "=" * 30,
        "",
        "Body part indexes:",
        str(np.asarray(arrays["_body_indexes"])),
        "",
        f"Total timesteps: {int(arrays['time_step_total'])}",
        "",
        "Data arrays summary:",
    ]
    ordered_names = [
        "joint_pos",
        "joint_vel",
        "body_pos_w",
        "body_quat_w",
        "body_lin_vel_w",
        "body_ang_vel_w",
        "_body_indexes",
        "time_step_total",
    ]
    for key in ordered_names:
        value = np.asarray(arrays[key])
        lines.append(f"  {key}: {value.shape} ({value.dtype})")
    return "\n".join(lines).rstrip() + "\n"


def sonic_body_indexes_to_storage_indexes(body_indexes, num_bodies):
    storage_indexes = []
    for body_idx in np.asarray(body_indexes, dtype=np.int64):
        if body_idx == 0:
            storage_idx = 0
        else:
            if body_idx < 1 or body_idx > 29:
                raise ValueError(
                    "SONIC body indexes must be within [0, 29] for G1 29-DOF, "
                    f"got {body_idx}"
                )
            storage_idx = int(MUJOCO_TO_ISAACLAB[body_idx - 1] + 1)

        if storage_idx < 0 or storage_idx >= num_bodies:
            raise ValueError(
                f"Mapped storage index {storage_idx} is out of range for model with {num_bodies} bodies"
            )
        storage_indexes.append(storage_idx)
    return np.asarray(storage_indexes, dtype=np.int64)


def convert_motion_file(input_path, output_dir, args, kinematics_model):
    motion_name = output_dir.name
    output_dir.mkdir(parents=True, exist_ok=True)

    motion_fps, root_pos, root_rot_xyzw, dof_pos_mujoco = load_gmr_motion(input_path)
    root_pos, root_rot_xyzw, dof_pos_mujoco, export_fps = resample_motion(
        root_pos,
        root_rot_xyzw,
        dof_pos_mujoco,
        src_fps=motion_fps,
        target_fps=args.target_fps,
    )

    root_pos = smooth_array(root_pos.astype(np.float32), args.smooth_window)
    dof_pos_mujoco = smooth_array(dof_pos_mujoco.astype(np.float32), args.smooth_window)
    root_rot_xyzw = smooth_quaternions_xyzw(root_rot_xyzw.astype(np.float32), args.smooth_window)
    dt = 1.0 / float(export_fps)

    body_indexes = np.asarray(args.body_indexes, dtype=np.int64)
    storage_indexes = sonic_body_indexes_to_storage_indexes(body_indexes, kinematics_model.num_joint)

    root_pos_t = torch.from_numpy(root_pos).to(device="cpu", dtype=torch.float32)
    root_rot_t = torch.from_numpy(root_rot_xyzw).to(device="cpu", dtype=torch.float32)
    dof_pos_mujoco_t = torch.from_numpy(dof_pos_mujoco).to(device="cpu", dtype=torch.float32)

    with torch.no_grad():
        body_pos_t, body_quat_xyzw_t = kinematics_model.forward_kinematics(
            root_pos_t,
            root_rot_t,
            dof_pos_mujoco_t,
        )

    if not args.no_ground_adjust:
        root_pos = root_pos.copy()
        ground_offset = compute_per_frame_ground_offset(
            body_pos_t,
            storage_indexes,
            args.ground_clearance,
            args.height_correct_window,
        )
        root_pos[:, 2] -= ground_offset
        root_pos_t = torch.from_numpy(root_pos).to(device="cpu", dtype=torch.float32)
        with torch.no_grad():
            body_pos_t, body_quat_xyzw_t = kinematics_model.forward_kinematics(
                root_pos_t,
                root_rot_t,
                dof_pos_mujoco_t,
            )

    body_pos_full = body_pos_t.cpu().numpy().astype(np.float32)
    body_quat_full_xyzw = normalize_quat_xyzw(body_quat_xyzw_t.cpu().numpy().astype(np.float32))

    body_pos_w = body_pos_full[:, storage_indexes, :].astype(np.float32)
    body_quat_selected_xyzw = ensure_quat_continuity_xyzw(body_quat_full_xyzw[:, storage_indexes, :])
    body_quat_w = body_quat_selected_xyzw[:, :, [3, 0, 1, 2]].astype(np.float32)

    # GMR dof_pos is in MuJoCo order. SONIC joint_pos.csv expects IsaacLab order.
    joint_pos = dof_pos_mujoco[:, MUJOCO_TO_ISAACLAB].astype(np.float32)
    joint_vel = finite_difference(joint_pos, dt)
    body_lin_vel_w = finite_difference(body_pos_w, dt)
    body_ang_vel_w = angular_velocity_from_quats_xyzw(body_quat_selected_xyzw, dt)

    joint_vel = smooth_array_gaussian(joint_vel, args.velocity_sigma)
    body_lin_vel_w = smooth_array_gaussian(body_lin_vel_w, args.velocity_sigma)
    body_ang_vel_w = smooth_array_gaussian(body_ang_vel_w, args.velocity_sigma)

    arrays = {
        "joint_pos": joint_pos,
        "joint_vel": joint_vel,
        "body_pos_w": body_pos_w,
        "body_quat_w": body_quat_w,
        "body_lin_vel_w": body_lin_vel_w.astype(np.float32),
        "body_ang_vel_w": body_ang_vel_w.astype(np.float32),
        "_body_indexes": body_indexes,
        "time_step_total": np.int64(joint_pos.shape[0]),
    }

    write_csv(
        output_dir / "joint_pos.csv",
        arrays["joint_pos"],
        [f"joint_{idx}" for idx in range(arrays["joint_pos"].shape[1])],
    )
    write_csv(
        output_dir / "joint_vel.csv",
        arrays["joint_vel"],
        [f"joint_vel_{idx}" for idx in range(arrays["joint_vel"].shape[1])],
    )
    write_csv(
        output_dir / "body_pos.csv",
        flatten_last_dims(arrays["body_pos_w"]),
        build_body_vector_header(len(body_indexes), ["x", "y", "z"]),
    )
    write_csv(
        output_dir / "body_quat.csv",
        flatten_last_dims(arrays["body_quat_w"]),
        build_body_vector_header(len(body_indexes), ["w", "x", "y", "z"]),
    )
    write_csv(
        output_dir / "body_lin_vel.csv",
        flatten_last_dims(arrays["body_lin_vel_w"]),
        build_body_vector_header(len(body_indexes), ["vel_x", "vel_y", "vel_z"]),
    )
    write_csv(
        output_dir / "body_ang_vel.csv",
        flatten_last_dims(arrays["body_ang_vel_w"]),
        build_body_vector_header(len(body_indexes), ["angvel_x", "angvel_y", "angvel_z"]),
    )

    (output_dir / "metadata.txt").write_text(build_metadata_text(motion_name, arrays))
    (output_dir / "info.txt").write_text(build_info_text(motion_name, arrays))

    print(f"Saved SONIC-style export to: {output_dir}")
    print(f"Frames: {joint_pos.shape[0]}, fps: {export_fps}")
    print(f"Body indexes: {body_indexes.tolist()}")
    print(f"Storage indexes in SONIC XML: {storage_indexes.tolist()}")


def resolve_default_output_dir(input_path):
    if input_path.is_dir():
        return input_path.parent / f"{input_path.name}_sonic"
    return input_path.parent / f"{input_path.stem}_sonic"


def iter_input_files(input_path, pattern):
    if input_path.is_file():
        if input_path.suffix != ".pkl":
            raise ValueError(f"Expected a .pkl input file, got: {input_path}")
        return [input_path]
    if input_path.is_dir():
        files = sorted(path for path in input_path.rglob(pattern) if path.is_file())
        if not files:
            raise FileNotFoundError(f"No files matching {pattern!r} found under: {input_path}")
        return files
    raise FileNotFoundError(f"Input path does not exist: {input_path}")


def build_output_dir_for_input(input_path, input_root, output_root):
    if input_root.is_file():
        return output_root
    relative_parent = input_path.relative_to(input_root).parent
    return output_root / relative_parent / input_path.stem


def main():
    args = parse_args()

    input_path = args.input.expanduser().resolve()
    output_root = (args.output_dir.expanduser() if args.output_dir else resolve_default_output_dir(input_path)).resolve()
    input_files = iter_input_files(input_path, args.pattern)
    sonic_xml = args.sonic_xml.expanduser().resolve()
    if not sonic_xml.is_file():
        raise FileNotFoundError(f"SONIC XML not found: {sonic_xml}")

    kinematics_model = KinematicsModel(str(sonic_xml), device="cpu")
    if kinematics_model.num_dof != 29:
        raise ValueError(
            f"Expected SONIC XML with 29 dof, got {kinematics_model.num_dof}: {sonic_xml}"
        )

    converted = 0
    skipped = 0
    for input_file in input_files:
        motion_output_dir = build_output_dir_for_input(input_file, input_path, output_root)
        metadata_path = motion_output_dir / "metadata.txt"
        if args.skip_existing and metadata_path.exists():
            print(f"[skip] {input_file} -> {motion_output_dir}")
            skipped += 1
            continue

        print(f"[convert] {input_file} -> {motion_output_dir}")
        convert_motion_file(input_file, motion_output_dir, args, kinematics_model)
        converted += 1

    if input_path.is_dir():
        print(
            f"Batch conversion finished. Converted: {converted}, skipped: {skipped}, output root: {output_root}"
        )


if __name__ == "__main__":
    main()
