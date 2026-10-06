# GMR — General Motion Retargeting

**Documentation only. Code, local patches, robot assets and body models are not bundled in this directory.**

GMR maps human motion to humanoid robot reference poses using inverse kinematics. It is a shared component rather than an additional confirmed baseline in the model roster.

- [Detailed Chinese guide](README_zh.md): installation, inputs/outputs, processing rationale, assumptions and validation limits.
- [Resources](resources.yaml)
- [Upstream GMR](https://github.com/YanjieZe/GMR)

The guide describes a previously inspected working copy with local changes. The baseline commit alone does not include those changes. Availability of a `--help` entry point is not evidence of clean installation, end-to-end reproduction or physically valid motion. A pinned release including the documented changes is still required.

The original GMR license and separate robot/body-model licenses remain applicable. SMPL-X model files must be obtained separately from their authorized source.
