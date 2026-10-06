> **历史运行说明：** 本文凡称“本包含源码、入口或参考结果”均指旧版完整环境；当前公开参考版已移除这些文件，命令不能直接运行。见 [公开范围](../../PUBLIC_SCOPE.md)。

# `demo_smpl_interleaved_batch.py`：有序视频/文本任务目录

**接受的输入**：`--input_root` 下每个子目录是一个任务；目录中放 `.txt` 与视频文件，文件名中的 `_order_N` 决定拼接顺序。可混排任意多段；一个 `.txt` 内多行会进一步展开为多个文本段。当前底层 `demo_smpl.py` 只接受 `.mp4/.avi/.mov`，所以本示范使用 `.mp4`。

本包有 `examples/interleaved/MIXED_01` 至 `MIXED_05` 五个任务。每个任务先用 `clip_order_01.mp4` 条件化，再用 `prompt_order_02.txt` 生成 100 帧。

```bash
cd /path/to/GEM_five_repro_delivery_20261006/five_demo
bash run/run_demo_smpl_interleaved_batch.sh
```

该运行脚本先执行 `--manifest_only`，生成 `outputs/interleaved/input_manifest.tsv`，再用清单执行五条推理。对应的直接命令为：

```bash
source run/common.sh
require_text_encoder
"$PYTHON_BIN" "$PACKAGE_ROOT/mini_repo/scripts/demo/demo_smpl_interleaved_batch.py" \
  --input_root "$PACKAGE_ROOT/examples/interleaved" \
  --output_root "$PACKAGE_ROOT/outputs/interleaved" \
  --manifest "$PACKAGE_ROOT/outputs/interleaved/input_manifest.tsv" \
  --manifest_only
CUDA_VISIBLE_DEVICES=0 "$PYTHON_BIN" "$PACKAGE_ROOT/mini_repo/scripts/demo/demo_smpl_interleaved_batch.py" \
  --input_root "$PACKAGE_ROOT/examples/interleaved" \
  --output_root "$PACKAGE_ROOT/outputs/interleaved" \
  --manifest "$PACKAGE_ROOT/outputs/interleaved/input_manifest.tsv" \
  --ckpt_path "$CKPT_PATH" --hmr2_ckpt "$HMR2_CKPT" \
  --text_length 100 --seed 1234 --resume
```

**查看结果**：`outputs/interleaved/MIXED_01/smpl_params.pt` 至 `MIXED_05/`；首次运行时 `outputs/interleaved/status_shard_0.tsv` 应有五行 `ok`，带 `--resume` 重跑时已有结果会标为 `skipped`。只看进程退出码不足以判断逐条成功。与 `demo_smpl.py` 相比，这个脚本额外管理任务目录、输入清单、固定种子、分片和逐条状态。

**后处理参考**：`reference_postprocess/gmr/interleaved/MIXED_01/` 有 SMPL-X `.npz` 和 G1 `.pkl`；SONIC CSV 在 `reference_postprocess/sonic/interleaved/MIXED_01/`。复算见 [后处理教程](../../POSTPROCESS.md)。
