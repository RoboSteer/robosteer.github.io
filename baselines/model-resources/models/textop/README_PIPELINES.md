> **历史教程 / Historical guide：** 下文凡称“本包包含源码、入口、参考结果”均指旧版完整工作环境，不适用于当前公开参考版。当前版仅供阅读，命令不能仅凭本目录运行。 Claims below that source, entrypoints or results are bundled describe the previous full environment, not this public reference edition. See [PUBLIC_SCOPE.md](PUBLIC_SCOPE.md).

# TextOp 文本到 G1 motion 与 SONIC CSV

按本教程准备环境和原作者资源，先运行随目录提供的一条文本样例，再用输入清单复现抽样任务。本目录整理了 TextOp 的 **TXT → RobotMDAR motion NPZ → SONIC CSV** 推理流程；模型结构和预训练权重归原作者所有，交付中的推理导出修改及来源见[源码与许可](PROVENANCE_zh.md)。这里不包含训练、TextOpTracker、ROS 部署或实体机器人控制。

## 输入和处理阶段

```text
TXT 文件（每行一条动作指令）
  → CLIP ViT-B/32 文本编码
  → TextOp RobotMDAR 顺序生成 G1 motion
  → motion.npz（50 FPS）
  → npz_to_csv.py
  → 六个 SONIC CSV + metadata.txt / info.txt
```

普通 TXT 输入的非空行按原顺序执行。**对于 `TXT/PRED` 文本预测任务，只导出占位指令对应的生成 motion**；前文生成段仅用于形成动作历史，不写入最终预测结果。TextOp 不会参考占位段后文；INTER 舍弃后文，RETRO 的文本条件只有首行占位指令。三类输入的实际处理方式见[预测方法说明](PRED_TASK_METHOD_zh.md)。

## 目录中有什么

| 路径 | 用途 |
| --- | --- |
| `scripts/`、`examples/` | 本项目检查脚本和公开文本示例；上游 TextOp 源码不在本包内 |
| `ENVIRONMENT_zh.md` | 已测试环境、安装顺序、权重与资源放置路径 |
| `REPRODUCTION_zh.md` | 普通 TXT 单条和 10 条样本的运行与检查命令 |
| `PREDICTION_zh.md`、`PRED_TASK_METHOD_zh.md` | FORE / INTER / RETRO 输入、处理边界及 30 条样本命令 |
| `examples/txt_sample10/`、`examples/pred_sample30/` | 获得提供者授权公开的 10 条普通文本与 30 条预测文本 |
| `input_samples.csv`、`input_samples_pred.csv` | 上述输入的相对路径、大小和哈希清单 |
| `pred_task_windows.csv` | 30 条原始预测任务的目标时间窗与任务 JSON 哈希 |
| `VALIDATION_zh.md`、`PROVENANCE_zh.md` | 已完成的验证及代码、资源来源 |
| `source_manifest.json`、`SHA256SUMS` | 当前参考包成员清单和解包目录文件校验清单 |

## 环境与资源

先按[环境与资源指南](ENVIRONMENT_zh.md)建立独立的 Python 3.8 环境，再从本目录的 `TextOp/` 安装 `deps/isaac_utils`、`TextOpRobotMDAR` 与 OpenAI CLIP。参考服务器为 Tesla V100、PyTorch 2.4.1+cu121。现有服务器流程已跑通；全新机器从零安装尚未完整验证。`environment-pip-freeze.txt` 是环境记录，不是一键安装脚本。

从 [TextOp 原作者资源库](https://huggingface.co/datasets/Yochish/TextOp-Data)自行获取 DAR、VAE 权重，以及相应统计量和 G1 描述资源，并按环境指南放进 `TextOp/TextOpRobotMDAR/` 的指定路径。交付目录包含上述少量验证文本，不包含外部模型资源、完整数据集或历史运行结果。CLIP `ViT-B/32` 也须在运行时可下载或已缓存。

## 先运行一条文本样例

在本目录执行以下命令。`demo_walk.txt` 已随源码提供；接入上述资源后，从项目目录运行：

```bash
cd TextOp/TextOpRobotMDAR
robotmdar --config-name=loop_dar \
  seed=0 headless=true \
  prompt_source=./inputs/check_one \
  save_csv.enabled=true save_csv.output_dir=./outputs/check_one \
  save_csv.write_npz=true save_csv.write_csv=false \
  save_csv.write_sidecar=true save_csv.postprocess_npz=false \
  save_csv.infer_batch_size=8 save_csv.clip_timesteps=100 \
  save_csv.merge_segments_by_source=true \
  ckpt.dar=./logs/pretrained/checkpoint/ckpt_200000.pth \
  guidance_scale=5.0 data.weighted_sample=true \
  data.datadir=./dataset/PRIVATE-DATA \
  data.action_statistics_path=./dataset/BABEL-AMASS-ROBOT-23dof-FULL-50fps/action_statistics.json \
  skeleton.asset.assetRoot=./description/robots/g1/
python scripts/npz_to_csv.py ./outputs/check_one --workers 4
```

命令先生成 `motion.npz`，再输出六个 SONIC CSV。转换命令不加 `--sidecar`，以保留生成阶段写入的侧记文件。重新尝试时使用新的输出目录，避免旧结果混入。10 条抽样文本已放在 `examples/txt_sample10/`；核对和运行步骤见[普通 TXT 教程](REPRODUCTION_zh.md)。

## 运行预测输入

以下“只导出占位指令生成段”的规则仅适用于 `TXT/PRED` 预测配置；普通 TXT 运行使用 `loop_dar` 配置，不按占位指令筛选。

FORE、INTER、RETRO 各 10 条验证文本已放在 `examples/pred_sample30/`。先用 `input_samples_pred.csv` 核对 SHA256，再按[预测任务教程](PREDICTION_zh.md)选择 `loop_dar_pred` 配置运行和导出。该流程已在参考服务器对 30 条样本完成生成与结构验收。每行指令生成时先跳过 20 帧预热，再为占位指令保留 100 帧（50 FPS 下 2 秒）；前文生成段不写进预测结果，后文不参与生成。没有按原始任务的目标时间窗再次切割，`pred_task_windows.csv` 可用于逐条对照。类别名表示输入原本的任务位置，不表示 TextOp 使用了后文。

## 输出与检查

以 `demo_walk.txt` 为例，输出位于：

```text
TextOp/TextOpRobotMDAR/outputs/check_one/demo_walk/motion.npz
TextOp/TextOpRobotMDAR/outputs/check_one_csv/demo_walk/
  metadata.txt  info.txt
  joint_pos.csv  joint_vel.csv
  body_pos.csv   body_quat.csv
  body_lin_vel.csv  body_ang_vel.csv
```

NPZ 是生成阶段的 G1 motion；CSV 是转换后的 SONIC 格式。当前转换检查 29 个关节和 14 个身体部位，CSV 行数应与 NPZ 帧数一致，数值应有限。具体字段和检查命令见[普通 TXT 教程](REPRODUCTION_zh.md)和[预测任务教程](PREDICTION_zh.md)。参考服务器上，普通文本 10/10、预测输入 30/30 通过文件结构与数值检查；细节见[验证记录](VALIDATION_zh.md)。这不等于动作质量、原任务指标或实体机器人安全验证。

在本目录运行 `sha256sum -c SHA256SUMS`，仅核对清单列出的解包目录文件；`source/TextOp_reference_20261006.tar.gz` 压缩包须另用同名 `.sha256` 文件核对。公开参考版不提供上游源码快照。固定随机种子仍不保证不同硬件和依赖版本下逐字节一致；比较结果时记录输入、权重、环境和实际命令。
