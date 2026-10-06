> **历史教程 / Historical guide：** 下文凡称“本包包含源码、入口、参考结果”均指旧版完整工作环境，不适用于当前公开参考版。当前版仅供阅读，命令不能仅凭本目录运行。 Claims below that source, entrypoints or results are bundled describe the previous full environment, not this public reference edition. See [PUBLIC_SCOPE.md](PUBLIC_SCOPE.md).

# UH-1 文本到 G1 SONIC：复现教程

UH-1 原作者提供语言条件的人形动作生成模型。本交付使用本地批量脚本，把文本逐行生成为 H1 动作，并可转换为 G1 SONIC 参考运动。本文说明实际可运行的输入、命令、输出和边界。首先阅读 [`ENVIRONMENT.md`](ENVIRONMENT.md) 和 [`RESOURCES.md`](RESOURCES.md) 准备环境与资源。

## 任务与流程

```text
TXT_GEN/*.txt ── scripts/inference.py ──────> H1 trajectory.npy ── convert_h1_to_g1_sonic.py ──> G1 SONIC/
TXT_{FORE,INTER,RETRO}/*.txt ── scripts/inference_pred.py ──> 占位指令的 H1 trajectory.npy ── 同上 ──> G1 SONIC/
```

每个 `.txt` 的非空行是一条英文动作描述。普通生成入口分别生成每一行的动作段，再拼为一条 H1 轨迹；段间只对齐根节点位置，并舍弃后段首帧。输出帧率为 20 Hz。预测入口也逐行生成，但只导出 `Generate smooth ... motion` 占位指令的帧；各行文本分别编码，**前文和后文都不会作为占位动作的条件**。因此其结果是占位指令的文本生成基线，不能称为真正的条件预测、插值或回溯。详见 [`PREDICTION.md`](PREDICTION.md)。

`examples/` 有 `TXT_GEN`、`TXT_FORE`、`TXT_INTER`、`TXT_RETRO` 各 10 条输入。`examples/input_samples.csv` 记录文件名、字节数、SHA256、非空行数和占位行数。源目录的其他数据不在交付包内。

在当前解包目录运行 `sha256sum -c SHA256SUMS`，仅核对清单列出的解包文件；`source/UH-1_public_reference_20261005.tar.gz` 压缩包须另用同名 `.sha256` 文件核对。样例抽样使用排序后的合格 `.txt` 列表和固定随机种子 `20261005` 至 `20261008`；合格条件是 UTF-8、1–10 条非空行，预测文件含相应占位指令，普通生成文件不含预测占位指令。

## 准备工作目录

以下命令从有权限使用 `internal/source/UH-1` 的完整交付目录执行。公开的参考资料不含 UH-1 源码快照；若要分发源码，先解决上游许可问题（见 [`PROVENANCE.md`](PROVENANCE.md)）。

```bash
cd UH-1_delivery_20261005/internal/source/UH-1
```

将从[原作者模型页](https://huggingface.co/USC-GVL/UH-1)自行取得的 `UH1_Action_Tokenizer.pth`、`UH1_Transformer.pth`，以及配套 `Mean.npy`、`Std.npy` 放在本目录，或统一放在 `checkpoints/UH-1/`。内部源码快照已保留两份小型统计文件。权重不随交付包提供。CLIP `ViT-B/32` 需能通过 `clip.load` 下载，离线运行时先缓存。准备 GMR 和 G1 XML/mesh 资源后，方可运行转换阶段；路径要求见 [`RESOURCES.md`](RESOURCES.md)。

## 一条普通生成样例

从源码目录运行，并给每次实验使用新的输出目录。下例所指样例是本包中选出的 5 行文本；`--gpu-ids` 应改为本机 GPU 编号。`--verify-load` 会重新读取生成文件以检查结构；运行记录存于 `--run-dir`。

```bash
python scripts/inference.py \
  --prompt-txt ../../../public/examples/TXT_GEN/L1_TXT_GEN_j7GG8UOpKi0_00002_0_68.txt \
  --gpu-ids 0 \
  --output-dir ../../../runs/gen \
  --run-dir ../../../runs/gen_record \
  --seed 1234 --verify-load
```

生成文件名是输入 basename 加 `_continuous_trajectory.npy`。验证 `runs/gen_record/summary.json` 中 `success=1`、`failed=0`、`unaccounted=0`，再检查 `results.jsonl` 和 `stages.jsonl`。`run_config.json` 记录参数、环境、代码提交、checkpoint 路径及可选哈希；`inputs.jsonl`、`inputs.txt` 记录样本。要记录权重哈希，可加 `--hash-checkpoints`（读取近 1 GB 权重，会增加启动时间）。

## 一条预测任务样例

```bash
python scripts/inference_pred.py \
  --prompt-txt ../../../public/examples/TXT_FORE/L1_TXT_FORE_b9m6sRcFrms_00006_0_108.txt \
  --gpu-ids 0 \
  --output-dir ../../../runs/pred \
  --run-dir ../../../runs/pred_record \
  --seed 1234 --verify-load
```

生成文件名以 `_pred_trajectory.npy` 结尾。`TXT_INTER` 和 `TXT_RETRO` 使用同一入口，把 `--prompt-txt` 换成对应样例。检查输出字典中的 `segments` 均对应占位指令，并对照 `source_num_frames` 与 `num_frames`；后者只计导出帧。预测文本中的其余描述会被生成用于脚本的拼接过程，但其帧不导出，也不改变占位动作的语义条件。默认会合并连续重复的同一占位指令。

## 批量运行与转换

```bash
python scripts/inference.py --prompt-txt ../../../public/examples/TXT_GEN \
  --gpu-ids 0 --output-dir ../../../runs/gen10 --run-dir ../../../runs/gen10_record --seed 1234
python scripts/convert_h1_to_g1_sonic.py \
  --input-dir ../../../runs/gen10 --output-root ../../../runs/gen10_g1 --jobs 1
```

批量预测应分别对 `TXT_FORE`、`TXT_INTER`、`TXT_RETRO` 运行，使用独立的输出目录和运行记录。不要把 `TXT_GEN` 传入预测入口。

```bash
for task in TXT_FORE TXT_INTER TXT_RETRO; do
  python scripts/inference_pred.py --prompt-txt "../../../public/examples/$task" \
    --gpu-ids 0 --output-dir "../../../runs/$task" \
    --run-dir "../../../runs/${task}_record" --seed 1234
done
for task in TXT_FORE TXT_INTER TXT_RETRO; do
  python scripts/convert_h1_to_g1_sonic.py \
    --input-dir "../../../runs/$task" --output-root "../../../runs/${task}_g1" --jobs 1
done
```

转换器将 H1 的 27 个关节映射至 G1 的 29 个关节，额外腰部两维置零；按 G1 XML 限位裁剪，再从 20 Hz 重采样到默认 50 Hz，执行地面对齐和正向运动学。每个输出目录含 `joint_pos.csv`、`joint_vel.csv`、`body_pos.csv`、`body_quat.csv`、`body_lin_vel.csv`、`body_ang_vel.csv`、`metadata.txt`、`info.txt`。关节位置是 29 维 IsaacLab 顺序；刚体是默认 14 个身体；世界位置单位米，四元数为 `wxyz`。转换器接受的输入 `.npy` 是 Python 字典，加载时需 `allow_pickle=True`，只应读取可信来源。

## 检查与限制

- 每次运行先看 `summary.json`、`results.jsonl`、`failures.jsonl`、`stages.jsonl`；失败样本可从 `failed_inputs.txt` 重跑。`--skip-existing` 只按文件存在跳过，建议先完成验证，再决定是否跳过。
- 文本生成不保证跨段关节角、姿态或速度连续。G1 转换不证明动作可在真实机器人上安全执行。
- 本包没有训练代码的验收、基准指标计算或历史结果数值一致性声明。最小样例运行状态见 [`VALIDATION.md`](VALIDATION.md)。
- 上游官方 `inference.py` 是单 prompt 示例；交付的批量入口为 `scripts/inference.py` 与 `scripts/inference_pred.py`。`Model_Record/模型运行命令/6.UH-1.md` 中的 15 万条估时属于历史批量计划，并非本交付验收。
