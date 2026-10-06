> **历史教程 / Historical guide：** 下文凡称“本包包含源码、入口、参考结果”均指旧版完整工作环境，不适用于当前公开参考版。当前版仅供阅读，命令不能仅凭本目录运行。 Claims below that source, entrypoints or results are bundled describe the previous full environment, not this public reference edition. See [PUBLIC_SCOPE.md](PUBLIC_SCOPE.md).

# 10 条文本样本验证记录

2026-10-04 在 <HOST> 上，使用本包对应的工作区源码、TextOp 原作者的 DAR/VAE checkpoint 和 `input_samples.csv` 所列的 10 条输入，完成了全新生成与 NPZ→CSV 转换。

| 检查 | 结果 |
| --- | --- |
| 10 条输入与清单的 SHA256 | 10/10 一致 |
| 新生成的 `motion.npz` | 10/10 存在且时间序列长度自洽、数值有限 |
| 转换得到的六个 SONIC CSV | 10/10 齐全；每个文件的行数与 NPZ 帧数一致，列数及数值检查通过 |
| 历史完整版公开示例的完整流程 | 从旧版交付压缩包解压源码、接入外部资源后，使用 `inputs/check_one/demo_walk.txt` 按教程的相对路径命令完成生成与转换，1/1 成功 |

本次输出中，`joint_pos.csv` 和 `joint_vel.csv` 各有 29 列；身体位置、四元数、线速度和角速度按 14 个身体部位导出。CSV 位于对应 NPZ 输出目录的同级 `_csv` 目录。实际命令、环境清单、输入副本、日志、输出及逐样本验证 JSON 保存在服务器交付目录的 `internal/`，不属于公开候选包。

另保留了这 10 条输入对应的历史输出。历史 CSV 使用旧版 30 个身体部位格式，已经单独标记和核验；用当前转换脚本从历史 NPZ 导出的 14 部位 CSV 也通过 10/10 检查。历史输出不应冒充本次全新生成结果。

样本从 `TXT_COMP_LEGS` 输入目录中筛选：只考虑含 1–5 条非空指令、且已有完整历史输出的文本，再以固定种子 `20261004` 抽取 10 条。这 10 条现已随包放在 `examples/txt_sample10/`，文件哈希与 `input_samples.csv` 逐条一致。因此它们适合作为短流程复现参考，**不代表整个目录的随机代表样本**。

这里检查的是文件结构、帧数、列数和有限数值；**未**检查跨机器逐字节一致性、动作质量或实体机器人安全性。参考环境的从零安装仍需在另一台机器验证。

## 30 条预测输入验证

从 `TXT/PRED/TXT_FORE`、`TXT_INTER`、`TXT_RETRO` 各取 10 条，输入 SHA256 核对 30/30 一致；这些文本现已随包放在 `examples/pred_sample30/`。三类样本均用 TextOp `loop_dar_pred` 配置重新生成，只保留占位段的前向预测结果；预测段 NPZ 与 `metadata.txt` 的占位指令、100 帧长度、字段形状及有限数值检查 30/30 通过；NPZ 转换后的六个 14 部位 SONIC CSV 与帧数、列数、有限数值检查 30/30 通过。单条预测样本也独立完成了生成、转换及预测段校验。内部验证记录见 `validation_pred_sample30.tsv` 与 `validation_pred_sample30_csv.json`。预测导出配置会截断占位指令之后的文本：INTER 后文舍弃，RETRO 的文本条件只有首行占位指令。

原始任务 JSON 的 `time_window` 已逐项核对并写入 `pred_task_windows.csv`。这 30 条的目标段长度为 0.4–7.144 秒；TextOp 固定 100 帧（2 秒）并未对齐原任务窗口。以上 30/30 结果仅表示生成文件可读且格式自洽，不能作为原任务的误差评测结果。

2026-10-05 另从本独立交付目录的源码和 `examples/pred_sample30/TXT_RETRO/` 读取 1 条输入，以服务器内部权重、统计量和 G1 资源完成重新生成、NPZ→CSV 转换及预测段校验，得到 `checked=1 success=1 failed=0 skipped=0`。该检查验证了新目录源码和样本路径可用于运行；外部资源仍需使用者自行准备，且全新机器安装尚未验证。
