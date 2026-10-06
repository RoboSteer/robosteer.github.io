# Motion format documentation

Status: schema documentation pending. This page does not establish a new universal motion format.

For each model, record file fields and shapes, units, coordinate axes and handedness, world/local semantics, rotation representation, joint ordering, robot resource version, frame rate, resampling and velocity calculation. State which fields are saved and which require reconstruction.

Several model guides now describe their own SMPL, robot-joint, or SONIC outputs; follow the selected model's field, frame-rate, coordinate, and joint-order contract. GMR's pose sequence is described in its [Chinese guide](../components/gmr/README_zh.md). Do not assume a GMR PKL, a model's intermediate motion file, and a SONIC CSV share one schema. A universal cross-model format has not been finalized.
