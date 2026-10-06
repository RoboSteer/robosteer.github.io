> **历史教程 / Historical guide：** 下文凡称“本包包含源码、入口、参考结果”均指旧版完整工作环境，不适用于当前公开参考版。当前版仅供阅读，命令不能仅凭本目录运行。 Claims below that source, entrypoints or results are bundled describe the previous full environment, not this public reference edition. See [PUBLIC_SCOPE.md](PUBLIC_SCOPE.md).

# 替换成自己的输入

五个推理入口的随包示范命令通常固定检查样例数量。加入新文件时请放到单独的 `five_demo/custom_inputs/`，并使用下面的直接 Python 命令及新的 `custom_outputs/`，避免与参考或旧结果混合。文本预测专用封装另接受自定义输入根目录，见第 2 节。路径和文件名可以自定，以下只展示可照抄的结构。

从交付根目录建立自己的输入目录。下面两行展示文件复制与文本写入；将 `/path/to/my_video.mp4` 改成实际路径：

```bash
cd /path/to/GEM_five_repro_delivery_20261006
mkdir -p five_demo/custom_inputs/mixed/CASE_01 five_demo/custom_inputs/text
cp /path/to/my_video.mp4 five_demo/custom_inputs/mixed/CASE_01/clip.mp4
printf '%s\n' 'a person walks forward' > five_demo/custom_inputs/mixed/CASE_01/prompt.txt
printf '%s\n' 'a person turns left' > five_demo/custom_inputs/text/my_01.txt
```

随后在交付根目录执行一次：

```bash
cd /path/to/GEM_five_repro_delivery_20261006
source five_demo/run/common.sh
require_text_encoder
require_video_assets
```

`source` 会设置 `PACKAGE_ROOT`、`GEM_ROOT`、`PYTHON_BIN` 等变量，并切换到 `GEM/`；后面命令沿用这些变量。已有 Python 环境可先设置 `PYTHON_BIN=/path/to/python`。如只做纯文本批量，可跳过 `require_video_assets`。

## 1. 单次混合 `demo_smpl.py`

准备 `custom_inputs/mixed/CASE_01/clip.mp4` 与 `prompt.txt`（例如一行 `a person walks forward`），或在参数中直接写 `text:a person walks forward`。视频和文本的顺序就是生成序列的顺序。

```bash
CUDA_VISIBLE_DEVICES="${GPU_ID:-0}" "$PYTHON_BIN" "$PACKAGE_ROOT/mini_repo/scripts/demo/demo_smpl.py" \
  --input_list "$PACKAGE_ROOT/custom_inputs/mixed/CASE_01/clip.mp4" \
               "$PACKAGE_ROOT/custom_inputs/mixed/CASE_01/prompt.txt" \
  --ckpt_path "$CKPT_PATH" --hmr2_ckpt "$HMR2_CKPT" \
  --text_length 100 --no_render \
  --output_root "$PACKAGE_ROOT/custom_outputs/mixed/CASE_01"
```

结果为 `custom_outputs/mixed/CASE_01/clip_mix/smpl_params.pt`。一次 `--input_list` 是一条序列；若要逐文件独立生成，使用下一个批量入口。

## 2. 文本批量 `demo_smpl_text_batch.py`

把每条任务写成单独 `.txt`，如 `custom_inputs/text/my_01.txt`、`my_02.txt`。文件中每条非空行是一段文本：

```bash
CUDA_VISIBLE_DEVICES="${GPU_ID:-0}" "$PYTHON_BIN" "$PACKAGE_ROOT/mini_repo/scripts/demo/demo_smpl_text_batch.py" \
  --input_dir "$PACKAGE_ROOT/custom_inputs/text" \
  --output_root "$PACKAGE_ROOT/custom_outputs/text" \
  --ckpt_path "$CKPT_PATH" --text_length 100 --batch_size 1
```

`my_01.txt` 对应 `custom_outputs/text/my_01/smpl_params.pt`。

### 文本预测：只导出生成段

TXT_FORE、TXT_INTER、TXT_RETRO 需要包含对应的完整指令行，并分别把指令放在条件描述之后、两段条件描述之间、条件描述之前。按下面的目录摆放自己的文本：

```text
custom_inputs/pred/TXT_FORE/walk_01.txt
custom_inputs/pred/TXT_INTER/turn_01.txt
custom_inputs/pred/TXT_RETRO/sit_01.txt
```

可以只建立其中一种任务目录。运行预测专用封装，它会保留原始完整 SMPL 结果，并另存只含目标生成段的结果：

```bash
PRED_INPUT_ROOT="$PACKAGE_ROOT/custom_inputs/pred" \
PRED_OUTPUT_ROOT="$PACKAGE_ROOT/custom_outputs/pred_01" \
bash "$PACKAGE_ROOT/run/run_text_pred_batch.sh"
```

结果分别在 `custom_outputs/pred_01/raw/` 与 `custom_outputs/pred_01/generated/`，按 TXT_FORE/INTER/RETRO 和文本文件名分目录保存。具体文本顺序、15 条随包样例及检查方法见 [文本预测教程](five_demo/guides/text_prediction.md)。

## 3. 视频 HPE `demo_smpl_hpe.py`

将视频放入 `custom_inputs/hpe/`，例如 `walk_01.mp4`。目录模式可放多条；单条可改用 `--video /absolute/path/walk_01.mp4`。

```bash
CUDA_VISIBLE_DEVICES="${GPU_ID:-0}" "$PYTHON_BIN" "$PACKAGE_ROOT/mini_repo/scripts/demo/demo_smpl_hpe.py" \
  --video_dir "$PACKAGE_ROOT/custom_inputs/hpe" \
  --output_root "$PACKAGE_ROOT/custom_outputs/hpe" \
  --ckpt_path "$CKPT_PATH" --hmr2_ckpt "$HMR2_CKPT" --yolo_ckpt "$YOLO_CKPT" \
  --no_render
```

`walk_01.mp4` 对应 `custom_outputs/hpe/walk_01/smpl_params.pt`；视频预处理缓存位于同目录的 `preprocess/`。

## 4. 视频预测 `demo_smpl_predict_batch.py`

至少建立一个 `VID_FORE_HUMAN`、`VID_RETRO_HUMAN`、`VID_INTER_HUMAN` 任务目录（或把 `HUMAN` 换成 `SKEL`）。FORE/RETRO 每条一个视频；INTER 必须配对，例如：

```text
custom_inputs/predict/VID_FORE_HUMAN/walk01_fore_input.mp4
custom_inputs/predict/VID_INTER_HUMAN/walk02_start.mp4
custom_inputs/predict/VID_INTER_HUMAN/walk02_end.mp4
```

```bash
CUDA_VISIBLE_DEVICES="${GPU_ID:-0}" "$PYTHON_BIN" "$PACKAGE_ROOT/mini_repo/scripts/demo/demo_smpl_predict_batch.py" \
  --input_dir "$PACKAGE_ROOT/custom_inputs/predict" \
  --output_root "$PACKAGE_ROOT/custom_outputs/predict" \
  --task_types fore inter retro --text_length 100 --seed 1234 \
  --ckpt_path "$CKPT_PATH" --hmr2_ckpt "$HMR2_CKPT" --yolo_ckpt "$YOLO_CKPT"
```

对应输出会保留任务目录，如 `custom_outputs/predict/VID_INTER_HUMAN/walk02/smpl_params.pt`。检查输出根目录的 `failed_samples_shard_0_of_1.jsonl` 是否为空或不存在；该脚本可能在单条失败后继续退出 0。

## 5. 交替混合 `demo_smpl_interleaved_batch.py`

每条任务一个子目录，文件名中的 `_order_N` 控制顺序：

```text
custom_inputs/interleaved/CASE_01/clip_order_01.mp4
custom_inputs/interleaved/CASE_01/prompt_order_02.txt
```

先生成输入清单，再运行：

```bash
"$PYTHON_BIN" "$PACKAGE_ROOT/mini_repo/scripts/demo/demo_smpl_interleaved_batch.py" \
  --input_root "$PACKAGE_ROOT/custom_inputs/interleaved" \
  --output_root "$PACKAGE_ROOT/custom_outputs/interleaved" \
  --manifest "$PACKAGE_ROOT/custom_outputs/interleaved/input_manifest.tsv" \
  --manifest_only
CUDA_VISIBLE_DEVICES="${GPU_ID:-0}" "$PYTHON_BIN" "$PACKAGE_ROOT/mini_repo/scripts/demo/demo_smpl_interleaved_batch.py" \
  --input_root "$PACKAGE_ROOT/custom_inputs/interleaved" \
  --output_root "$PACKAGE_ROOT/custom_outputs/interleaved" \
  --manifest "$PACKAGE_ROOT/custom_outputs/interleaved/input_manifest.tsv" \
  --ckpt_path "$CKPT_PATH" --hmr2_ckpt "$HMR2_CKPT" \
  --text_length 100 --seed 1234
```

结果为 `custom_outputs/interleaved/CASE_01/smpl_params.pt`；逐任务成败写在 `status_shard_0.tsv`。输入、资源或参数变化时请换一个输出根，避免已有缓存影响结果。
