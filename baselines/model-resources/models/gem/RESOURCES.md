> **历史教程 / Historical guide：** 下文凡称“本包包含源码、入口、参考结果”均指旧版完整工作环境，不适用于当前公开参考版。当前版仅供阅读，命令不能仅凭本目录运行。 Claims below that source, entrypoints or results are bundled describe the previous full environment, not this public reference edition. See [PUBLIC_SCOPE.md](PUBLIC_SCOPE.md).

# 五个 demo 的模型资源与放置位置

交付包包含源码、样例和参考中间结果，不包含以下模型权重。请从相应权利人取得文件并核对使用条款。下表的大小与 SHA256 用于识别与本包配置匹配的资源文件；下载版本不同时，请先核实模型来源。

| 文件 | 哪些入口需要 | 获取线索 | 放置在交付根目录下 | 配套文件大小 / SHA256 |
| --- | --- | --- | --- | --- |
| `gem_smpl.ckpt` | 全部五个 | [NVIDIA GEM-X 模型页](https://huggingface.co/nvidia/GEM-X) | `GEM/inputs/pretrained/gem_smpl.ckpt` | 5,518,923,941 B / `1d15cbe2864d6de61a75e83fdbfe83bec3c7b183eee3d3dcdbd9107e4456454a` |
| `SMPLX_NEUTRAL.npz` | 全部五个；模型初始化需要 | [SMPL-X 官方注册下载](https://smpl-x.is.tue.mpg.de/) | `GEM/inputs/checkpoints/body_models/smplx/SMPLX_NEUTRAL.npz` | 108,752,058 B / `376021446ddc86e99acacd795182bbef903e61d33b76b9d8b359c2b0865bd992` |
| T5-3B 编码器 `model.safetensors` | 除纯 HPE 外 | [Hugging Face t5-3b](https://huggingface.co/t5-3b)；提取方法见下文 | `resources/t5-3b-encoder/model.safetensors` | 4,963,663,160 B / `44eede3af2a9f349d0c551cffd1e99d9a706185731b980e1e9e7fede886d2b33` |
| `epoch=10-step=25000.ckpt` | 含视频的四个入口 | [4D-Humans HMR2](https://github.com/shubham-goel/4D-Humans)；上游 GEM 安装说明给出的 [GVHMR 模型目录](https://drive.google.com/drive/folders/1eebJ13FUEXrKBawHpJroW0sNSxLjh9xD) | `GEM/inputs/checkpoints/hmr2/epoch=10-step=25000.ckpt` | 2,709,494,041 B / `2dcf79638109781d1ae5f5c44fee5f55bc83291c210653feead9b7f04fa6f20e` |
| `vitpose-h-multi-coco.pth` | 含视频的四个入口 | [ViTPose-H](https://github.com/ViTAE-Transformer/ViTPose)；上游 GEM 安装说明给出的 [GVHMR 模型目录](https://drive.google.com/drive/folders/1eebJ13FUEXrKBawHpJroW0sNSxLjh9xD) | `GEM/inputs/checkpoints/vitpose/vitpose-h-multi-coco.pth` | 2,549,075,546 B / `50e33f4077ef2a6bcfd7110c58742b24c5859b7798fb0eedd6d2215e0a8980bc` |
| `yolov8x.pt` | 含视频的四个入口 | [Ultralytics YOLOv8](https://docs.ultralytics.com/models/yolov8/) 与 [官方资源发布页](https://github.com/ultralytics/assets/releases) | `GEM/yolov8x.pt` | 136,890,692 B / `3df4ada6b4dad6d657868f2fdf7faecfb34dcfccf3a25c4b82079064718524c8` |

“含视频的四个入口”指 `demo_smpl.py` 的本包混合示例、`demo_smpl_hpe.py`、`demo_smpl_predict_batch.py` 和 `demo_smpl_interleaved_batch.py`。T5 目录还需要官方同版本的 `config.json`、`spiece.model`，建议一并放入 `tokenizer.json`。`preflight.sh` 会逐项检查。

## T5 编码器准备

从官方 `t5-3b` 下载完整的 `model.safetensors`、`config.json`、`spiece.model`、`tokenizer.json`。官方完整权重的 SHA256 为 `a0e6c24ae12dd1c39e454fede314b20311c9e83e9e785b0141e8586010ef7766`，大小 11,406,460,256 B。交付包中的提取工具先验证完整文件，再原样提取编码器与共享嵌入张量：

```bash
cd /path/to/GEM_five_repro_delivery_20261006
.venv/bin/python GEM/tools/extract_t5_encoder.py \
  /path/to/official-t5-3b/model.safetensors \
  resources/t5-3b-encoder/model.safetensors
cp /path/to/official-t5-3b/config.json /path/to/official-t5-3b/spiece.model \
   /path/to/official-t5-3b/tokenizer.json resources/t5-3b-encoder/
```

权重放好后运行 `bash preflight.sh --verify-hashes`。该命令会读取约 16 GB 权重；不想等待时先运行 `bash preflight.sh`，它检查路径、非空文件、环境和 GPU。模型文件不匹配已验证哈希时，不能据本包的历史结果声称使用了相同资源。

即使使用 `--no_render`，模型初始化仍需 `SMPLX_NEUTRAL.npz`。这份人体模型受官方许可限制，请自行注册取得，不能随本包转发。继续运行 GMR/SONIC 后处理时，还需要另一份 SMPL-X `.pkl` 与机器人资源；它们在下节说明。

## GMR/SONIC 后处理资源

完整流水线还需 GMR 源码、获许可的 `SMPLX_NEUTRAL.pkl`、G1 机器人资产，以及 SONIC G1 XML/网格；这些文件不在压缩包中。获取版本、放置路径、哈希与安装命令见 [POSTPROCESS.md](POSTPROCESS.md)。`.npz` 人体模型不能代替 `.pkl`。随包的 `five_demo/reference_postprocess/` 是运行产物，不是这些模型资源的副本。
