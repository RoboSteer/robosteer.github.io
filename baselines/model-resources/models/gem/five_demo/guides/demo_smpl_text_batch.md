> **历史运行说明：** 本文凡称“本包含源码、入口或参考结果”均指旧版完整环境；当前公开参考版已移除这些文件，命令不能直接运行。见 [公开范围](../../PUBLIC_SCOPE.md)。

# `demo_smpl_text_batch.py`：逐文件文本批量

**接受的输入**：`--input_dir` 指向含 `.txt` 文件的目录，可递归；每个文件是一个独立样例，文件内每条非空行是一个连续文本段。本包的 `examples/text_batch/` 下有 TXT_GEN、TXT_COMP_HANDS、TXT_COMP_LEGS、TXT_FORE、TXT_INTER、TXT_RETRO 六个标签目录，各 5 个文件。

例如，`TXT_GEN/TXT_GEN_01.txt` 的全文是 `body stays centered facing forward`。`TXT_FORE/TXT_FORE_01.txt` 有两行：`Square shoulders, controlled tension` 和 `Generate smooth future motion`；脚本会把两行依次作为两个文本段。直接修改一个样例文件即可替换提示词，保持 `.txt` 扩展名即可。

```bash
cd /path/to/GEM_five_repro_delivery_20261006/five_demo
bash run/run_demo_smpl_text_batch.sh TXT_GEN
```

直接调用：

```bash
source run/common.sh
require_text_encoder
CUDA_VISIBLE_DEVICES=0 "$PYTHON_BIN" "$PACKAGE_ROOT/mini_repo/scripts/demo/demo_smpl_text_batch.py" \
  --input_dir "$PACKAGE_ROOT/examples/text_batch/TXT_GEN" \
  --output_root "$PACKAGE_ROOT/outputs/text_batch/TXT_GEN" \
  --ckpt_path "$CKPT_PATH" --text_length 100 --batch_size 1 --resume
```

**查看结果**：`outputs/text_batch/TXT_GEN/TXT_GEN_01/smpl_params.pt` 至 `TXT_GEN_05/`。更换命令最后的任务标签可运行其他五组。`--batch_size` 可以增大，但同批样例段数不同时会分组；示范使用 1，降低显存需求。

一次处理六组各 5 条：`bash run/run_all_text_batch.sh`，结果按原任务目录保存在 `outputs/text_batch_all/`，应有 30 个 `smpl_params.pt`。

**后处理参考**：`reference_postprocess/gmr/text_batch_all/TXT_GEN/TXT_GEN_01/` 有 SMPL-X `.npz` 和 G1 `.pkl`；对应 SONIC CSV 在 `reference_postprocess/sonic/text_batch_all/TXT_GEN/TXT_GEN_01/`。其余任务保持相同路径规则，复算见 [后处理教程](../../POSTPROCESS.md)。

**任务边界**：COMP_HANDS/LEGS 只是文件夹名称，本脚本没有手/腿关节掩码。FORE/INTER/RETRO 文件可读入，但本脚本保留条件和生成文本的完整序列；如需只导出预测生成段，请使用 [文本预测专用封装](text_prediction.md)。
