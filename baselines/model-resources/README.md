---
pretty_name: RoboSteer Model Resources
language:
  - en
  - zh
tags:
  - robotics
  - motion-generation
  - documentation
---
# RoboSteer Model Resources — public reference edition

[中文说明](README_zh.md) · [Release scope](PUBLIC_RELEASE_SCOPE.md) · [MIT scope](LICENSE_SCOPE.md) · [Model index](model_index.csv)

This repository publishes project-authored guides and reference scripts for nine motion and robot pipelines. **All nine model entries are reference material.** None is a self-contained, publicly reproducible model release: upstream project source, checkpoints, body models, and robot assets must be obtained separately under their own terms. Historical validation records describe runs in the original environments; they do not establish a fresh installation from these files.

| Model | Current public material | Main missing dependency |
| --- | --- | --- |
| [MotionCraft](models/motioncraft/README.md) | Reference pipeline scripts and guides | Upstream MotionCraft, GMR and SONIC source and resources |
| [GEM](models/gem/README.md) | Five-task scripts, constructed examples and SMPL-X/G1/SONIC reference results | Upstream GEM, GMR and SONIC source and resources |
| [Language of Motion](models/language_of_motion/README_EN.md) | Reference tools and guides | Upstream LoM, GMR and SONIC source and resources |
| [ListenDenoiseAction](models/listen_denoise_action/README.md) | Original adapters and orchestration | Upstream LDA and GMR source and resources |
| [TextOp](models/textop/README.md) | Reference guide, original checker and text examples | Upstream TextOp source and resources |
| [UH-1](models/uh1/README.md) | Guides and text examples | Upstream UH-1 source and resources |
| [UniAct](models/uniact/README_EN.md) | Reference tools and guides | Upstream UniAct, GMR and SONIC source and resources |
| [video2robot](models/video2robot/README_EN.md) | Reference scripts and guides | Upstream video2robot, PromptHMR, GMR and resources |
| [BFM-Zero](models/bfm_zero/README.md) | Reference guide and provenance | Unpublished project adapter and upstream resources |

The files are for inspecting workflows and adapting them with independently obtained dependencies. Commands in older detailed guides record historical runs; some refer to files deliberately excluded from this public edition. Start with each model's `PUBLIC_SCOPE.md` before using them.

This is a file collection, not a `load_dataset()` table. Project-authored scripts and original documentation are available under the [MIT License](LICENSE) within the [stated scope](LICENSE_SCOPE.md). The MIT grant does not extend to upstream projects, weights, inputs, or generated results. Consult [third-party notices](THIRD_PARTY_NOTICES.md) and each model's source links. [Installation conventions](docs/installation.md) explain the reference-only status. Verify an archive with its adjacent `.sha256`; a directory `SHA256SUMS` covers only the listed unpacked files.
