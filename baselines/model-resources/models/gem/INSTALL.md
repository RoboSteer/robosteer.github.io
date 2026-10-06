> **历史教程 / Historical guide：** 下文凡称“本包包含源码、入口、参考结果”均指旧版完整工作环境，不适用于当前公开参考版。当前版仅供阅读，命令不能仅凭本目录运行。 Claims below that source, entrypoints or results are bundled describe the previous full environment, not this public reference edition. See [PUBLIC_SCOPE.md](PUBLIC_SCOPE.md).

# 从零配置环境

以下步骤适用于配备 NVIDIA GPU 的 Linux 机器。请按顺序安装依赖、放置模型资源，再运行预检和样例。每台机器都应以自己的 `preflight.sh` 和 `run_smoke.sh` 结果确认配置是否可用。

## 1. 准备机器

单卡运行脚本默认使用 GPU 0；可通过 `GPU_ID=1` 选择第二张 GPU。建议准备 Python 3.10、支持 CUDA 12.4 PyTorch 的 NVIDIA 驱动、至少一张 16 GB 显存 GPU，以及至少 50 GB 可用磁盘（含下载完整 T5、提取编码器和安装依赖时的临时空间；大量输出另计）。若计划渲染或导出视频，还应安装 `ffmpeg`/`ffprobe`。在提供 Python 3.10 系统包的 Ubuntu 版本上可运行：

```bash
sudo apt-get update
sudo apt-get install -y python3.10 python3.10-venv ffmpeg
nvidia-smi
```

不同发行版请安装等价软件；系统驱动和 CUDA 版本以目标机器为准。这里的 `sudo` 只用于系统依赖，模型运行不需要管理员权限。
若没有系统包安装权限，可使用一个自带 `venv`/`ensurepip` 的 Python 3.10 解释器，并以 `PYTHON_310=/absolute/path/to/python bash install_env.sh` 指定它。

## 2. 解压并核对交付包

```bash
sha256sum -c GEM_five_reference_20261006.tar.gz.sha256
tar -xzf GEM_five_reference_20261006.tar.gz
cd GEM_five_repro_delivery_20261006
sha256sum -c SHA256SUMS
```

目录 `GEM/` 是运行所需的 GEM 源码快照；`five_demo/mini_repo/scripts/demo/` 是五个入口及共用代码的副本，其中三处入口的示例或默认数据路径已改为可移植路径，原文件哈希见 `five_demo/SOURCE_MANIFEST.tsv`；`five_demo/examples/` 是输入；`five_demo/reference_outputs/` 是随包提供的参考中间结果；`five_demo/outputs/` 初始为空，供本机重新运行。`GEM/README_PIPELINES.md` 说明另一个文本到 SONIC 流水线；`GEM/README_UPSTREAM.md` 保留上游说明，其中部分 `docs/` 链接不在此裁剪版源码中。本包的五入口操作以当前目录的教程为准。

## 3. 建立 Python 环境

```bash
bash install_env.sh
```

脚本按顺序建立 `.venv/`，安装 PyTorch 2.6.0 CUDA 12.4、[配套依赖版本](requirements-runtime.txt)、Ultralytics 8.3.80，并以 editable 模式安装 `GEM/`。上游 `GEM/setup.cfg` 中的 NumPy、timm、Ultralytics 版本钉住了较旧值，故最后两步使用 `--no-deps`，避免覆盖本包指定的版本。使用已有兼容环境时可跳过安装，先执行 `export PYTHON_BIN=/absolute/path/to/python`，再运行本页的预检与验收命令。

安装需要能访问 Python 包索引。若计算节点不通外网，在能访问包索引的节点安装，或先准备同版本 wheel 仓库，再执行：

```bash
PIP_NO_INDEX=1 PIP_FIND_LINKS=/path/to/wheels bash install_env.sh
```

PyTorch 镜像索引可通过 `TORCH_INDEX_URL` 修改。如果创建虚拟环境时提示缺少 `ensurepip`，请安装 `python3.10-venv` 或换用自带 `venv` 的 Python 3.10。如果下载依赖时提示 DNS 或网络错误，请改用能联网的节点或离线 wheel 仓库。

## 4. 放置模型资源

按 [RESOURCES.md](RESOURCES.md) 取得并放置模型权重、SMPL-X 人体模型和 T5 配置文件。预期目录：

```text
GEM_five_repro_delivery_20261006/
  GEM/inputs/pretrained/gem_smpl.ckpt
  GEM/inputs/checkpoints/body_models/smplx/SMPLX_NEUTRAL.npz
  GEM/inputs/checkpoints/hmr2/epoch=10-step=25000.ckpt
  GEM/inputs/checkpoints/vitpose/vitpose-h-multi-coco.pth
  GEM/yolov8x.pt
  resources/t5-3b-encoder/{model.safetensors,config.json,spiece.model,tokenizer.json}
```

已有资源不必再次复制：可按同样相对路径放经许可的符号链接，或设置 `CKPT_PATH`、`HMR2_CKPT`、`GEM_T5_PATH`。SMPL-X、ViTPose 以及混合/交替入口的 YOLO 路径写在源码中，必须按上表放置；`YOLO_CKPT` 只会覆盖 HPE 和视频预测入口的 YOLO 路径。脚本默认离线运行，缺文件会在预检中报错。

## 5. 预检与最小验收

```bash
bash preflight.sh --verify-hashes
bash run_smoke.sh
```

`run_smoke.sh` 依次运行五个入口：混合 1 条、文本生成 5 条、HPE 5 条、视频 FORE/HUMAN 5 条、交替混合 5 条；最后逐文件检查 21 个 `smpl_params.pt` 的形状、有限值、片段范围和失败清单。日志在 `five_demo/run_logs/`，本次输出在 `five_demo/outputs/`。参考数据在 `five_demo/reference_outputs/`，可直接对照目录和片段类型。

## 6. 跑完所有随包样例

```bash
bash run_full.sh
```

应得到混合 5、六类文本 30、HPE 5、六类视频预测 30、交替混合 5，共 75 条目标结果；脚本最后调用 `verify_outputs.py --profile full`。如果先执行过最小验收，已完成样例会由 `--resume` 跳过，且 `outputs/` 还会保留单类文本和单类预测各 5 个额外结果，因此直接数全部 `smpl_params.pt` 可能得到 85。改变输入、权重或代码时请将旧 `five_demo/outputs/` 移作备份并重新建立空目录，避免读取过时结果。

失败时先看 `five_demo/run_logs/` 对应入口，再看单样例 `preprocess/`、视频预测的 `failed_samples_shard_0_of_1.jsonl`、交替任务的 `status_shard_0.tsv`。不要只依据进程退出码判断批量任务成功。

## 7. 文本预测：提取生成段

`run_full.sh` 中的 TXT_FORE、TXT_INTER、TXT_RETRO 结果保留了条件文本段与预测生成段。如果只需要预测生成段，另运行：

```bash
bash five_demo/run/run_text_pred_batch.sh
```

封装会检查输入指令顺序，并将 15 条预测任务的完整结果与生成段分别写入 `five_demo/outputs/text_pred/raw/` 和 `five_demo/outputs/text_pred/generated/`。运行结束应显示 `text prediction verification: PASS (15 tasks)`。处理自己的输入时按 [文本预测教程](five_demo/guides/text_prediction.md) 指定新的输入和输出目录。

## 8. 继续转换为 G1 和 SONIC

按照 [POSTPROCESS.md](POSTPROCESS.md) 准备独立的 GMR 环境、SMPL-X `.pkl` 和 SONIC G1 XML/网格，再运行：

```bash
bash run_postprocess.sh
```

该命令从五入口全量结果及文本预测生成段中选择 75 条任务，依次生成 SMPL-X `.npz`、G1 `.pkl` 和 SONIC CSV，并逐条核对。参考后处理产物位于 `five_demo/reference_postprocess/`；自己的运行结果位于 `five_demo/postprocess_outputs/`。
