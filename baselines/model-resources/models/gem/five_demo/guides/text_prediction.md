> **历史运行说明：** 本文凡称“本包含源码、入口或参考结果”均指旧版完整环境；当前公开参考版已移除这些文件，命令不能直接运行。见 [公开范围](../../PUBLIC_SCOPE.md)。

# 文本预测任务：FORE、INTER、RETRO

`demo_smpl_text_batch.py` 把一个 `.txt` 中的每条非空行依次生成一段动作，保存的是**条件段与预测段的完整序列**。需要把预测生成段单独交给下游时，使用 `run/run_text_pred_batch.sh`。这个封装先调用原文本批量入口，再按指令行筛出预测段；五个 GEM 推理入口本身不需要改动。

这里的条件也是文本描述，脚本会为这些描述生成动作段；它不读取已观测的动作轨迹。FORE、INTER、RETRO 表示文本段的位置和筛选规则，不等同于基于真实运动观测的未来预测。

## 输入怎么放

把每条任务写成独立 `.txt`，按任务放到以下目录。文件中必须且只能出现一次对应的完整指令行：

| 目录 | 文本行顺序 | 要导出的段 |
| --- | --- | --- |
| `TXT_FORE/` | 已知动作描述 → `Generate smooth future motion` | 未来动作 |
| `TXT_INTER/` | 起始动作描述 → `Generate smooth transition motion` → 结束动作描述 | 中间过渡 |
| `TXT_RETRO/` | `Generate smooth preceding motion` → 已知动作描述 | 前序动作 |

随包的 `examples/text_batch/TXT_FORE/`、`TXT_INTER/`、`TXT_RETRO/` 各有 5 条样例；封装只读取这三个目录，忽略同级的 TXT_GEN 和 TXT_COMP 目录。每条非空行默认生成 100 帧，预测段也是 100 帧。

## 运行样例

先按 [安装步骤](../../INSTALL.md) 放好环境、GEM 权重、SMPL-X 和 T5 文件。进入交付包根目录运行：

```bash
bash five_demo/run/run_text_pred_batch.sh
```

脚本会验证输入行的顺序，在 `five_demo/outputs/text_pred/input_manifest.tsv` 记录输入相对路径与 SHA256，然后生成两套结果：

```text
five_demo/outputs/text_pred/
  raw/TXT_FORE/TXT_FORE_01/smpl_params.pt        条件段 + 未来生成段
  generated/TXT_FORE/TXT_FORE_01/smpl_params.pt  仅未来生成段
  raw/TXT_INTER/TXT_INTER_01/smpl_params.pt       起始段 + 过渡段 + 结束段
  generated/TXT_INTER/TXT_INTER_01/smpl_params.pt 仅过渡生成段
  raw/TXT_RETRO/TXT_RETRO_01/smpl_params.pt       前序生成段 + 条件段
  generated/TXT_RETRO/TXT_RETRO_01/smpl_params.pt 仅前序生成段
```

运行结束应显示 `text prediction verification: PASS (15 tasks)`。验证会逐个检查原始结果的段数、筛选结果的指令、帧数、SMPL 张量形状与有限值。

## 换成自己的输入

在自定义根目录下创建一个或多个 `TXT_FORE/`、`TXT_INTER/`、`TXT_RETRO/` 子目录；每个子目录可放任意数量的 `.txt`。例如：

```text
/data/my_pred_text/TXT_FORE/walk_01.txt
/data/my_pred_text/TXT_INTER/turn_01.txt
```

指定输入和新的输出目录：

```bash
PRED_INPUT_ROOT=/data/my_pred_text \
PRED_OUTPUT_ROOT=/data/my_pred_outputs \
bash five_demo/run/run_text_pred_batch.sh
```

可用 `PRED_TEXT_LENGTH=120` 调整每段帧数、`PRED_BATCH_SIZE=2` 调整单次推理的样例数、`GPU_ID=1` 选择 GPU。每次更换输入、权重或参数时，请指定一个新的 `PRED_OUTPUT_ROOT`；封装拒绝覆盖已有的 SMPL 结果，以免新旧任务混在一起。

这个封装只导出 GEM 的 SMPL 参数，不执行 GMR/SONIC 后处理。它筛选的是文本指令对应的生成段，不会自动证明预测动作的语义质量。

后续用交付根目录的 `run_postprocess.sh` 转换生成段；随包对应的 GMR 与 SONIC 文件位于 `reference_postprocess/{gmr,sonic}/text_pred_generated/TXT_FORE/TXT_FORE_01/` 等任务目录。输入条件段不进入这组后处理结果，步骤见 [后处理教程](../../POSTPROCESS.md)。
