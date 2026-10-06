> **历史运行说明：** 本文凡称“本包含源码、入口或参考结果”均指旧版完整环境；当前公开参考版已移除这些文件，命令不能直接运行。见 [公开范围](../../PUBLIC_SCOPE.md)。

# `demo_smpl_hpe.py`：视频到 SMPL

**接受的输入**：`--video` 指定一个视频，或 `--video_dir` 递归读取目录；扩展名支持 `.mp4/.avi/.mov/.mkv/.webm`。两者选其一。输入视频须能解码且人物可被检测。该入口没有文本条件。

本包提供 `examples/video_hpe/video_01.mp4` 至 `video_05.mp4` 五段现存关键帧静态视频副本：

```bash
cd /path/to/GEM_five_repro_delivery_20261006/five_demo
bash run/run_demo_smpl_hpe.sh
```

直接调用：

```bash
source run/common.sh
CUDA_VISIBLE_DEVICES=0 "$PYTHON_BIN" "$PACKAGE_ROOT/mini_repo/scripts/demo/demo_smpl_hpe.py" \
  --video_dir "$PACKAGE_ROOT/examples/video_hpe" --limit 5 \
  --output_root "$PACKAGE_ROOT/outputs/video_hpe" \
  --ckpt_path "$CKPT_PATH" --hmr2_ckpt "$HMR2_CKPT" --yolo_ckpt "$YOLO_CKPT" \
  --no_render
```

**查看结果**：`outputs/video_hpe/video_01/smpl_params.pt` 至 `video_05/`，预处理文件在各样例的 `preprocess/`。这个入口的 SMPL 是整段观测视频的人体重建，没有额外预测生成段。GMR 中间结果和 SONIC CSV 分别在 `reference_postprocess/gmr/video_hpe/video_01/` 与 `reference_postprocess/sonic/video_hpe/video_01/`；复算见 [后处理教程](../../POSTPROCESS.md)。
