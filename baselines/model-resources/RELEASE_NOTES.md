# Initial documentation release — 2026-09-18

- Added English and Chinese landing pages and a machine-readable model index.
- Added information forms and resource/validation placeholders for nine recorded models/pipelines.
- Model roster corrected to nine models/pipelines; shared components are counted separately.
- Added project-neutral GMR usage documentation with processing rationale and explicit code-availability limitations.
- Added reusable model information, README, resource and validation templates.
- No model code, weights, runtime configuration, private logs or datasets are included in this release.

## Component update — 2026-09-18

- Added GR00T-WholeBodyControl documentation and information forms as the second shared component.
- Removed unnamed model placeholders and added component_index.csv.
- No component code, weights or runtime assets are included in this update.

## GEM reproduction bundle — 2026-10-06

- Replaced GEM placeholders with a bilingual five-entrypoint reproduction guide, source snapshot, sample inputs, reference outputs, postprocessing results and a checked archive.
- GEM weights, licensed SMPL-X models and robot assets remain external; fresh-machine installation has not been independently validated.
- Updated repository indexes and notices. Use the archive SHA256 file and bundled `SHA256SUMS` for GEM integrity checks.

## Repository status alignment — 2026-10-06

- Reconciled the bilingual landing pages, `model_index.csv`, and model roster with the files now present in all nine model directories. The directories range from source bundles and adapters to documentation, code links, and example outputs; they are not all complete standalone reproductions.
- Fixed model links that pointed to removed information forms or differently named README files.
- Updated third-party notices and installation/format guidance. Model checkpoints and licensed human-body/robot assets remain external; use each model's own validation record and checksum files.
- Removed the outdated 2026-09-18 scaffold `release_manifest.json` from the current branch. Use per-model checksum files for current deliveries.

## Public reference edition — 2026-10-06

- Rebuilt model archives to remove upstream source copies, pretrained models, robot assets, server logs, and machine-specific resource bindings. The MotionCraft archive no longer contains the Unitree G1 asset directory.
- Marked all nine model directories as reference material. Historical commands and validation records do not claim direct reproduction from the current public files.
- Added public scope notes, separate archive checksums where needed, and repaired TextOp's omitted-upstream-document links.
- Clarified the public edition's license scope. Earlier archive versions may remain in external caches.

## MIT downstream grant and history withdrawal — 2026-10-06

- Licensed project-authored scripts and original documentation under MIT, with explicit exclusions for third-party material, inputs, and generated results. Added the same notice to the rebuilt reference archives.
- Superseded archives are subject to repository history cleanup. External caches and previously downloaded copies may persist and must be assessed separately.
