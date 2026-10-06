# Third-party notices

This package contains adapters and orchestration files only. It does not redistribute upstream LDA source, checkpoints, audio/reference data, SMPL-X models, or G1/SONIC XML and mesh assets. Every external resource listed in `resources/resources.yaml` has `included: false` and must be obtained under its own terms.

## ListenDenoiseAction

The upstream project is `https://github.com/simonalexanderson/ListenDenoiseAction`. Its license restricts use to academic research and prohibits unauthorized redistribution. The public package therefore links to the upstream repository and does not include its full source or checkpoints. Use the upstream license and obtain permission before redistributing upstream files or derivative patches.

Citation: Alexanderson, Nagy, Beskow, and Henter, “Listen, Denoise, Action! Audio-Driven Motion Synthesis with Diffusion Models,” ACM Transactions on Graphics 42(4), 2023. [arXiv:2211.09707](https://arxiv.org/abs/2211.09707), [DOI: 10.1145/3592458](https://doi.org/10.1145/3592458).

## GMR

The GMR source is `https://github.com/YanjieZe/GMR` and is distributed by its upstream project under MIT terms. The current public reference edition does not copy GMR source or the earlier GMR overlay files. Obtain GMR directly from upstream and preserve its notices.

## Unitree G1 assets

G1 assets may carry a separate BSD-3-Clause notice. Obtain the exact asset revision and retain its notice. This package does not include G1 XML or mesh files.

## SMPL-X

SMPL-X body models are obtained separately from `https://smpl-x.is.tue.mpg.de/` under the official model terms. They are not bundled.

Official model terms: `https://smpl-x.is.tue.mpg.de/modellicense.html`.

## TISA audio features

The upstream LDA pipeline refers to TISA for audio feature extraction. Cite the [TISA repository](https://github.com/ulmewennberg/tisa) and Wennberg et al., “TISA: A Tool for Incremental Speech and Music Analysis,” [ACL 2021](https://aclanthology.org/2021.acl-short.18), when using that feature path. TISA files are not bundled here.

## SONIC / GR00T

The SONIC/G1 XML source is [NVlabs/GR00T-WholeBodyControl](https://github.com/NVlabs/GR00T-WholeBodyControl). The exact asset revision is recorded in `resources/resources.yaml`; confirm the repository's current asset and redistribution terms before copying XML or meshes into another release.

## New adapter code

The RoboSteer adapter author has confirmed authorship and permission for public redistribution. Original RoboSteer adapter and orchestration files are released under the MIT License in the package-level `LICENSE` file, with copyright holder `cxt`. This grant does not cover upstream LDA files, weights, SMPL-X models, or robot assets.

## Citation

GMR: [YanjieZe/GMR](https://github.com/YanjieZe/GMR), MIT code license; preserve the separate BSD-3-Clause notice for the G1 asset directory. If the retargeting method is discussed, cite Araújo et al., “Retargeting Matters: General Motion Retargeting for Humanoid Motion Tracking,” [arXiv:2510.02252](https://arxiv.org/abs/2510.02252). See `INFORMATION_zh.md` for the consolidated citation list.
