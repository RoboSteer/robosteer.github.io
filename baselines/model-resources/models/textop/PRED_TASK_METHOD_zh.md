> **历史教程 / Historical guide：** 下文凡称“本包包含源码、入口、参考结果”均指旧版完整工作环境，不适用于当前公开参考版。当前版仅供阅读，命令不能仅凭本目录运行。 Claims below that source, entrypoints or results are bundled describe the previous full environment, not this public reference edition. See [PUBLIC_SCOPE.md](PUBLIC_SCOPE.md).

# TextOp 对 TXT/PRED 输入的处理方法

## 原任务与输入

本交付使用的 `TXT_FORE`、`TXT_INTER`、`TXT_RETRO` 文本来自 `level1/text/processed/TXT/PRED/`。预处理脚本 `level1/text/scripts/rewrite_txt_tasks_to_t2m.py` 从任务 JSON 的文本字段改写动作描述，并将待生成段写成固定占位指令。FORE 是前文加未来占位；INTER 是前文、过渡占位、后文；RETRO 是前序占位加后文。

这些文本文件没有观测运动轨迹，原任务 JSON 的 `Background` 等文字也可能在改写时被丢弃。因此，这里复现的是 **TextOp 对改写后文本输入的处理方法**，不是利用真实运动锚点的插帧或回溯。[任务窗口清单](pred_task_windows.csv)记录了 30 条原始任务 JSON 的哈希、时长和目标时间窗。目标段长为 0.4–7.144 秒，而当前 TextOp 命令固定导出 100 帧，即 50 FPS 下的 2 秒。

## 三类输入如何运行

TextOp 根据文本生成 motion 时按指令顺序向前采样，不会回头参考后文来修改已生成的动作。因此，本包对预测任务只保留 TextOp **前向预测处理结果**，即占位指令对应的生成段。三类输入都按 [预测任务教程](PREDICTION_zh.md)使用同一个 `loop_dar_pred` 配置；RobotMDAR 每次编码当前一行文本，并使用已生成动作的短历史。配置中的 `trim_prompts_after_last_kept=true` 还会在推理前截去占位指令之后的文本行。

每条占位指令先跳过 20 帧预热，再收集并截取 100 帧；只导出这个生成段，不导出前文生成段，也不按原始任务 JSON 的时间窗再切一次。预测配置没有添加站立引入段或混合过渡帧。随后 NPZ→CSV 只改变输出格式和身体部位选择，不再裁剪时间轴。

| 输入类别 | 本次进入生成过程的条件 | 输出应如何理解 |
| --- | --- | --- |
| FORE | 前文生成的动作历史及末行占位指令 | 保留前向预测生成段；没有真实运动观测锚点 |
| INTER | 前文生成的动作历史及中间的占位指令；后文舍弃 | 保留仅依赖前文的前向生成段，不能视为利用两端条件的插值 |
| RETRO | 文本条件只有首行占位指令；其后的文本全部舍弃 | 保留从首行指令开始的前向生成段，不能视为利用后文的回溯 |

这 30 条都是实际运行得到的 **TextOp 前向处理输出**，INTER 和 RETRO 也作为该方法的结果与样例保留。三类结果均按原输入类别标记，类别名只说明占位指令在原文本中的位置，不表示模型使用了后文。不能据此声称已完成双向条件插值、回溯，或原任务的完整指标复现。关闭截断开关本身也不能使自回归模型用未来行改变已生成的占位段。

[预测输入清单](input_samples_pred.csv)中的 30 条输出已通过文件结构、帧数和有限数值检查；检查范围和命令见 [验证记录](VALIDATION_zh.md)及 [预测任务教程](PREDICTION_zh.md)。这些检查不衡量动作质量，也不证明与原任务目标时间窗或后文条件一致。本版交付仅包含 TextOp 流程。
