> **历史教程 / Historical guide：** 下文凡称“本包包含源码、入口、参考结果”均指旧版完整工作环境，不适用于当前公开参考版。当前版仅供阅读，命令不能仅凭本目录运行。 Claims below that source, entrypoints or results are bundled describe the previous full environment, not this public reference edition. See [PUBLIC_SCOPE.md](PUBLIC_SCOPE.md).

# TXT → RobotMDAR → SONIC CSV 运行教程

以下命令从交付目录根目录（含 `README_PIPELINES.md` 的目录）开始。先按 [环境与资源](ENVIRONMENT_zh.md)完成安装与资源准备。输入目录中每个 `.txt` 文件是一条样本，文件内非空行按原顺序形成指令序列。

## 1. 运行一条样本

源码包已提供 `inputs/check_one/demo_walk.txt`，内容是两行简短动作描述。先用它检查整条流程，再替换为自己的文本。执行：

```bash
cd TextOp/TextOpRobotMDAR
robotmdar --config-name=loop_dar \
  seed=0 \
  headless=true \
  prompt_source=./inputs/check_one \
  save_csv.enabled=true \
  save_csv.output_dir=./outputs/check_one \
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
python scripts/npz_to_csv.py ./outputs/check_one --workers 4
```

转换脚本会在同级建立 `outputs/check_one_csv/`，把六个 SONIC CSV 和侧记文件写入对应样本目录；`outputs/check_one/` 保留原始 `motion.npz`。`npz_to_csv.py` 此处**不加 `--sidecar`**，因为生成阶段已写入侧记文件；避免转换时覆盖原始运行记录。每次新尝试使用新的输出目录。`save_csv.clip_timesteps=100` 表示每条指令段按历史协议截取 100 帧，最终导出为 50 FPS。

## 2. 运行 10 条抽样文本

这 10 条文本已放在本交付目录的 `examples/txt_sample10/`，其相对路径和 SHA256 见[输入样本清单](input_samples.csv)。先核对哈希，再从 `TextOp/TextOpRobotMDAR` 运行上面的命令，将 `prompt_source` 改为 `../../examples/txt_sample10`、`save_csv.output_dir` 改为 `./outputs/sample10`，转换命令的输入目录改为 `./outputs/sample10`。运行参数和 checkpoint 与单条检查保持一致。若从其他位置复制样本，请保留清单中的文件名，并重新核对哈希。

## 3. 核对输出

每个输入样本应对应两个以原文件名（不含 `.txt`）命名的输出目录，分别保存生成阶段和转换阶段的产物：

```text
outputs/sample10/<sample_id>/motion.npz
outputs/sample10_csv/<sample_id>/metadata.txt
outputs/sample10_csv/<sample_id>/info.txt
outputs/sample10_csv/<sample_id>/joint_pos.csv
outputs/sample10_csv/<sample_id>/joint_vel.csv
outputs/sample10_csv/<sample_id>/body_pos.csv
outputs/sample10_csv/<sample_id>/body_quat.csv
outputs/sample10_csv/<sample_id>/body_lin_vel.csv
outputs/sample10_csv/<sample_id>/body_ang_vel.csv
```

检查输出目录个数是否与输入条数一致，NPZ 中各时间序列帧数是否一致，六个 CSV 的数据行数是否与 NPZ 帧数相同，数据是否均为有限数值。`npz_to_csv.py` 会检查 29 个关节和 14 个 SONIC 身体部位等格式假设；其中四元数顺序、关节顺序和地面对齐细节应以随包代码为准。数值校验通过不表示动作可安全用于实体机器人。

输出目录、日志和私有配置可能包含服务器路径，公开前需单独审查。固定随机种子也不保证跨机器逐字节复现；记录实际环境、权重哈希、输入哈希和完整命令，才能比较运行条件。
