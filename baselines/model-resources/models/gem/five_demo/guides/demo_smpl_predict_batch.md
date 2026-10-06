> **历史运行说明：** 本文凡称“本包含源码、入口或参考结果”均指旧版完整环境；当前公开参考版已移除这些文件，命令不能直接运行。见 [公开范围](../../PUBLIC_SCOPE.md)。

# `demo_smpl_predict_batch.py`：视频条件预测

**接受的输入**：顶层目录名必须包含 `VID_RETRO_HUMAN/SKEL`、`VID_FORE_HUMAN/SKEL`、`VID_INTER_HUMAN/SKEL`。RETRO/FORE 每样例一个视频；INTER 要有同名前缀的 `_start.mp4` 与 `_end.mp4`（也接受其他支持的视频扩展名）。脚本会自动插入三种固定文本指令，可用 `--prompt_retro/fore/inter` 覆盖。

本包 `examples/video_predict/` 有六个目录：RETRO、FORE、INTER × HUMAN、SKEL，每目录 5 个样例；INTER 为 5 对视频。先跑一类：

例如，`VID_INTER_HUMAN/human01_start.mp4` 和 `human01_end.mp4` 是一对，脚本会在两段视频之间插入 `Generate smooth transition motion`。FORE 的 `human01_fore_input.mp4` 会在视频后插入 `Generate smooth future motion`；RETRO 则在视频前插入 `Generate smooth preceding motion`。

```bash
cd /path/to/GEM_five_repro_delivery_20261006/five_demo
bash run/run_demo_smpl_predict_batch.sh fore HUMAN
```

直接调用：

```bash
source run/common.sh
require_text_encoder
CUDA_VISIBLE_DEVICES=0 "$PYTHON_BIN" "$PACKAGE_ROOT/mini_repo/scripts/demo/demo_smpl_predict_batch.py" \
  --input_dir "$PACKAGE_ROOT/examples/video_predict/VID_FORE_HUMAN" \
  --output_root "$PACKAGE_ROOT/outputs/video_predict/VID_FORE_HUMAN" \
  --task_types fore --limit 5 --text_length 100 --seed 1234 --resume \
  --ckpt_path "$CKPT_PATH" --hmr2_ckpt "$HMR2_CKPT" --yolo_ckpt "$YOLO_CKPT"
```

**查看结果**：`outputs/video_predict/VID_FORE_HUMAN/human01/smpl_params.pt` 至 `human05/`。其 `segment_info` 包含输入视频段和生成文本段；如果需要仅保留生成段，可以在单独的输出目录使用 `--keep-generated-only`，该选项会改变保存的 SMPL 内容。

一次处理六类的命令是 `bash run/run_all_video_predict.sh`，预期 30 个 `smpl_params.pt`。脚本自身会继续处理单样例失败，务必检查 `outputs/video_predict_all/failed_samples_shard_0_of_1.jsonl` 和实际成功数。本包的视频是静态关键帧示范，INTER 的 start/end 取相邻视频，只验证格式与操作流程，不用于预测质量评价。

**后处理参考**：`reference_postprocess/gmr/video_predict_all/VID_FORE_HUMAN/human01/` 有 SMPL-X `.npz` 和 G1 `.pkl`；SONIC CSV 在对应的 `reference_postprocess/sonic/` 路径。这里转换的是包含观测段与生成段的完整序列，详见 [后处理教程](../../POSTPROCESS.md)。
