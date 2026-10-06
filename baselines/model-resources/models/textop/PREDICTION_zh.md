> **历史教程 / Historical guide：** 下文凡称“本包包含源码、入口、参考结果”均指旧版完整工作环境，不适用于当前公开参考版。当前版仅供阅读，命令不能仅凭本目录运行。 Claims below that source, entrypoints or results are bundled describe the previous full environment, not this public reference edition. See [PUBLIC_SCOPE.md](PUBLIC_SCOPE.md).

# TextOp FORE / INTER / RETRO 预测输入处理

先阅读[原任务与模型适配](PRED_TASK_METHOD_zh.md)。本页记录 TextOp 对三类预测输入的实际处理方法：统一只保留占位段的前向预测结果。TextOp 生成 motion 时不会参考后文；INTER 的占位段后文舍弃，RETRO 的文本条件只有首行占位指令。

这三类输入来自 `level1/text/processed/TXT/PRED/`。每个文本文件包含上下文动作描述和一行预测占位指令：

| 类别 | 占位指令 | 位置与用途 |
| --- | --- | --- |
| `TXT_FORE` | `Generate smooth future motion` | 末行，生成后续动作 |
| `TXT_INTER` | `Generate smooth transition motion` | 上下文之间，生成过渡动作 |
| `TXT_RETRO` | `Generate smooth preceding motion` | 首行，生成前序动作 |

[预测输入清单](input_samples_pred.csv)对每类列出 10 条，记录相对路径、文件大小、SHA256、非空行数和占位指令行号。这 30 条文本已放在 `examples/pred_sample30/`，保持与清单一致的相对路径。抽样规则：将每个类别中有效文件按 `SHA256("TextOp-PRED-release-20261004/" + 相对路径)` 排序，取前 10 条；要求占位指令恰好出现一次，FORE 在末行，RETRO 在首行。运行前按清单核对哈希。

## 运行

先完成 [环境与资源准备](ENVIRONMENT_zh.md)，回到交付目录根目录（含 `README_PIPELINES.md` 的目录）。原任务目标时间窗见 [任务窗口清单](pred_task_windows.csv)；本 TextOp 命令固定输出 100 帧。下列命令直接读取交付目录的 `examples/pred_sample30/`，使用与常规 TXT 流程相同的模型、统计量和 G1 资源，但选择预测配置：

```bash
cd TextOp/TextOpRobotMDAR
robotmdar --config-name=loop_dar_pred \
  seed=0 headless=true \
  prompt_source=../../examples/pred_sample30 \
  save_csv.enabled=true \
  save_csv.output_dir=./outputs/pred_sample30 \
  save_csv.write_npz=true \
  save_csv.write_csv=false \
  save_csv.write_sidecar=true \
  save_csv.postprocess_npz=false \
  save_csv.infer_batch_size=8 \
  save_csv.clip_timesteps=100 \
  save_csv.merge_segments_by_source=true \
  ckpt.dar=./logs/pretrained/checkpoint/ckpt_200000.pth \
  guidance_scale=5.0 \
  data.weighted_sample=true \
  data.datadir=./dataset/PRIVATE-DATA \
  data.action_statistics_path=./dataset/BABEL-AMASS-ROBOT-23dof-FULL-50fps/action_statistics.json \
  skeleton.asset.assetRoot=./description/robots/g1/
python scripts/npz_to_csv.py ./outputs/pred_sample30 --workers 4
```

转换时**不加 `--sidecar`**，以保留生成阶段写入的 `metadata.txt` 和 `info.txt`。CSV 出现在 `outputs/pred_sample30_csv/`。每行指令生成时先跳过 20 帧预热，再收集并截取 100 帧；预测配置只导出占位指令对应的前向生成结果，不把上下文动作帧写入最终 NPZ，也不按原始任务 JSON 的时间窗再次切割。`metadata.txt` 记录参与此次运行的指令序列及实际导出指令。配置中的 `trim_prompts_after_last_kept=true` 使占位指令之后的文本行不会参与此次生成。FORE 使用前文生成的动作历史；INTER 保留前文、舍弃后文；RETRO 的占位指令位于首行，文本条件只有该指令。此处复现的是当前工作区的实际预测导出行为，不能据此声称双向上下文插值。NPZ→CSV 转换保留 100 个时间步，但将 30 个身体部位数据选择为 SONIC 所需的 14 个部位。

## 校验

随源码包提供 `scripts/check_pred_exports.py`。从 `TextOp/TextOpRobotMDAR` 运行：

```bash
find "$(realpath ../../examples/pred_sample30)" -type f -name '*.txt' | sort > pred_input_manifest.txt
python scripts/check_pred_exports.py \
  --manifest pred_input_manifest.txt \
  --source-root "$(realpath ../../examples/pred_sample30)" \
  --output-root "$(realpath outputs/pred_sample30)" \
  --status-file pred_validation.tsv \
  --clip-timesteps 100 --output-fps 50 \
  --instructions 'Generate smooth future motion|Generate smooth transition motion|Generate smooth preceding motion'
```

应得到 `checked=30 success=30 failed=0 skipped=0`。脚本核对输入指令、metadata 中实际导出段、NPZ 字段、帧数与有限数值。再检查 `_csv` 目录下每条样本的六个 SONIC CSV；它们属于转换结果，不能替代 NPZ/metadata 的预测段校验。重新运行时使用新的输出目录，避免混入旧结果。
