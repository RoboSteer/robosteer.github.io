> **历史运行说明：** 本文凡称“本包含源码、入口或参考结果”均指旧版完整环境；当前公开参考版已移除这些文件，命令不能直接运行。见 [公开范围](../../PUBLIC_SCOPE.md)。

# `demo_smpl.py`：单次文本、视频或混合序列

**接受的输入**：`--input_list` 后面按顺序放 `.mp4/.avi/.mov`、`.txt` 或 `text:动作描述`。一个 `.txt` 中每条非空行会成为一个新文本段，默认每段 100 帧。`--input_dir` 是另一模式，只递归读取 `.txt` 并逐文件生成独立结果；两种模式不能同时给出。

**本包样例**：`examples/single_mixed/MIXED_01/clip.mp4` 是视频条件，`prompt.txt` 是一行生成描述；`MIXED_01` 至 `MIXED_05` 各有一对。运行第 1 条：

第 1 条的 `prompt.txt` 全文是 `body stays centered facing forward`。更换视频和提示词时保留这两个文件名，或直接修改 `--input_list` 后的路径。

```bash
cd /path/to/GEM_five_repro_delivery_20261006/five_demo
bash run/run_demo_smpl.sh 01
```

直接调用的核心参数等价于：

```bash
source run/common.sh
require_text_encoder
CUDA_VISIBLE_DEVICES=0 "$PYTHON_BIN" "$PACKAGE_ROOT/mini_repo/scripts/demo/demo_smpl.py" \
  --input_list "$PACKAGE_ROOT/examples/single_mixed/MIXED_01/clip.mp4" \
               "$PACKAGE_ROOT/examples/single_mixed/MIXED_01/prompt.txt" \
  --ckpt_path "$CKPT_PATH" --hmr2_ckpt "$HMR2_CKPT" \
  --text_length 100 --no_render --resume \
  --output_root "$PACKAGE_ROOT/outputs/demo_smpl/MIXED_01"
```

**查看结果**：`outputs/demo_smpl/MIXED_01/clip_mix/smpl_params.pt`。`segment_info` 应依次出现 `video` 与 `text` 两段。切换 02–05 时，运行脚本会分开写入 `MIXED_02..05/`，避免同名 `clip.mp4` 覆盖结果。

**后处理参考**：`reference_postprocess/gmr/demo_smpl/MIXED_01/clip_mix/` 有 SMPL-X `.npz` 和 G1 `.pkl`；对应 SONIC CSV 在 `reference_postprocess/sonic/demo_smpl/MIXED_01/clip_mix/`。复算方法见 [后处理教程](../../POSTPROCESS.md)。

**易混点**：一次 `--input_list` 传入五个 `.txt` 会生成**一条五段序列**，不是五个独立样例；要逐文件处理，请用 `--input_dir` 或 `demo_smpl_text_batch.py`。本入口只识别 `.mp4/.avi/.mov` 视频。
