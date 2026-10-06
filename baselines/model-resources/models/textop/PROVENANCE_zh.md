> **历史教程 / Historical guide：** 下文凡称“本包包含源码、入口、参考结果”均指旧版完整工作环境，不适用于当前公开参考版。当前版仅供阅读，命令不能仅凭本目录运行。 Claims below that source, entrypoints or results are bundled describe the previous full environment, not this public reference edition. See [PUBLIC_SCOPE.md](PUBLIC_SCOPE.md).

# 源码来源、范围与许可

- 上游项目：[TeleHuman/TextOp](https://github.com/TeleHuman/TextOp)，工作区基线提交 `37e3caa53f644a95fb4b60a4412d31ae69f885a4`；根目录 `LICENSE.md` 为 MIT License。
- 历史完整版曾包含工作区源码快照；当前公开参考包已移除该快照，只保留原创检查脚本、教程和少量文本示例。当前 `source_manifest.json` 仅列出参考包成员。
- 当前交付范围为原创预测结果检查脚本、参考教程和文本示例；上游 `TextOpRobotMDAR/robotmdar`、`deps/isaac_utils`、原版说明和许可证文件不再复制。`TextOpRobotMDAR/inputs/check_one/demo_walk.txt` 是本次编写的公开合成示例，不来自原始数据集。TextOpTracker、TextOpDeploy、训练数据与历史结果不在此包中。
- DAR/VAE checkpoint、统计量和 G1 描述资源由[原作者资源库](https://huggingface.co/datasets/Yochish/TextOp-Data)提供；本包只给获取链接和预期路径。上游 `USAGE.md` 还要求遵守 Unitree MuJoCo、BeyondMimic、AMASS、BABEL-TEACH 和 LAFAN1 等资源的许可。
- 本包未完成实体机器人部署或安全验证。`examples/txt_sample10/` 和 `examples/pred_sample30/` 收录输入提供者授权公开的少量验证文本；相应清单记录路径、大小和哈希。运行结果未入包。

本次补充的 `scripts/check_pred_exports.py` 来自当前 TextOp 工作区的预测结果校验脚本。`input_samples_pred.csv` 是对随包 30 条验证文本的哈希清单。

`pred_task_windows.csv` 来自服务器上的 SteerableMotionBenchmarkDataset 原始公开任务 JSON，仅收录每条任务的来源相对路径、文件哈希和时间窗；JSON 副本留在内部目录。

## 上游完整文档

公开参考包不附带上游源码或上游 README。原快照中失效的封面、数据集和部署相对链接改为原项目的在线文件：
[封面](https://github.com/TeleHuman/TextOp/blob/main/docs/Cover.jpg)、[DATASET.md](https://github.com/TeleHuman/TextOp/blob/main/DATASET.md)、[unitree_mujoco 说明](https://github.com/TeleHuman/TextOp/blob/main/TextOpDeploy/src/unitree_mujoco/readme.md)。这些链接指向上游当前 `main`，内容可能不同于记录的工作区基线。
