# Release candidate validation — 2026-10-04

Version: 0.1.0-rc1. Scope: existing-environment pipeline and portable entry points.

This is a public summary. The full 10-sample logs, generated artifacts, environment records, and server paths remain in the internal preparation workspace and are intentionally not bundled.

## Environment configuration policy

This delivery uses the existing, already verified `lda` and `gmr` environments as its runtime baseline. Fresh Conda installation is not an acceptance requirement. The files under `environment/` document a migration recipe (Python, CUDA wheel, direct dependencies, constraints, and optional proxy setup); they are not a clean-install lockfile and are not claimed as freshly installed and imported on the verification server.

## Code alignment

See code_alignment.json. Four LDA adapters, synthesize.py and GMR smpl.py are identical to the 10-sample server run. GMR's two CLI scripts only replace private default paths / require explicit inputs; numerical code is unchanged.

## Checks performed

- Python syntax and shell syntax passed.
- All three command builders handled paths containing spaces, retained intermediate outputs and avoided writes during dry-run.
- Nonempty output directories were rejected before launching child processes.
- An isolated LDA/GMR source copy with the candidate overlays completed all three shell entry points on EL6yyP9_AZg_00059_0_53_music.
- Stage exits: 0 / 0 / 0. Runtime approximately 22.97 / 28.49 / 3.16 seconds.
- Output reload checks passed: 64 feature/BVH/SMPL-X/G1 frames; 106 SONIC frames at the requested 50 FPS; finite values; 29 robot DOFs and normalized quaternions.
- Features, BVH, robot PKL and all six SONIC CSV files are byte-identical to the same sample in the earlier 10-sample run. This comparison does not cover all ten samples on the candidate overlays or claim cross-device bitwise determinism.

Machine-readable evidence: wrapper_smoke_summary.json. Full logs and generated artifacts are retained in the internal preparation workspace, not bundled here.

## Remaining limits

This test intentionally used the existing, already verified LDA/GMR environments and existing resources. Fresh Conda installation and dependency resolution are outside this delivery scope; the existing environments remain the run baseline. Official-download byte verification, physical tracking, and redistribution rights remain unverified.

The overlay application helper checks fixed upstream commits and clean working copies; the isolated smoke copy was assembled directly from source and overlays, not cloned from public network sources. Do not treat this as a clean-install test.
