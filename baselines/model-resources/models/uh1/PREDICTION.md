> **历史教程 / Historical guide：** 下文凡称“本包包含源码、入口、参考结果”均指旧版完整工作环境，不适用于当前公开参考版。当前版仅供阅读，命令不能仅凭本目录运行。 Claims below that source, entrypoints or results are bundled describe the previous full environment, not this public reference edition. See [PUBLIC_SCOPE.md](PUBLIC_SCOPE.md).

# 预测任务文本的实际处理

`TXT_FORE`、`TXT_INTER`、`TXT_RETRO` 文件由动作描述行和一条可能重复的占位指令组成：

| 目录 | 被保留的占位指令 |
| --- | --- |
| `TXT_FORE` | `Generate smooth future motion` |
| `TXT_INTER` | `Generate smooth transition motion` |
| `TXT_RETRO` | `Generate smooth preceding motion` |

`scripts/inference_pred.py` 对每个非空行独立调用 CLIP 和 UH-1 Transformer，生成一个动作段；随后按输入顺序拼接所有段。拼接时将后段 root position 对齐前段末尾，并删除后段第一帧。最后仅截取占位指令对应的帧，保存为 `*_pred_trajectory.npy`。连续重复的相同占位行默认合并为一条；可用 `--keep-repeated-placeholders` 保留旧行为。

因此三类文本任务都只导出占位指令的生成段。`FORE` 的前文、`INTER` 的前后文、`RETRO` 的后文不会进入占位指令的文本编码器，也没有动作历史条件。前面已经生成的动作段可能影响保留段的 **root position 平移** 和首帧删除，但不改变生成段的姿态内容。`RETRO` 中占位指令位于开头时，后文完全不会影响输出段。该方法不能评估条件式未来预测、插值或回溯能力。

输出字典包含 `segments`、`source_prompts`、`context_prompts`、`source_num_frames`、`num_frames`。`segments` 的区间采用左闭右开 `[start_frame,end_frame)`；`source_num_frames` 是筛选前拼接长度，`num_frames` 是导出的长度。查看这两个字段和 `run_record/results.jsonl` 可核对是否按预期只保留占位段。脚本默认 `--seed 1234`，但未保证所有 CUDA 算子严格确定性。
