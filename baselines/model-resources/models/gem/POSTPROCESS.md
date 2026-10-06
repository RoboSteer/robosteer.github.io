> **历史教程 / Historical guide：** 下文凡称“本包包含源码、入口、参考结果”均指旧版完整工作环境，不适用于当前公开参考版。当前版仅供阅读，命令不能仅凭本目录运行。 Claims below that source, entrypoints or results are bundled describe the previous full environment, not this public reference edition. See [PUBLIC_SCOPE.md](PUBLIC_SCOPE.md).

# 从 SMPL 运行到 G1 与 SONIC

五个 demo 先生成 `smpl_params.pt`。本页把这些结果继续转换为 SMPL-X 动作、GMR 的 29 关节 G1 轨迹和 SONIC CSV。随包的 `five_demo/reference_postprocess/` 保存全部 95 个参考 SMPL 文件对应的三阶段产物；正式运行自己的样例时，推荐处理 75 个互不重复的任务结果。此流程只验证文件与数值格式，不代表机器人实机可安全执行。

## 1. 准备外部代码和资源

先按 [INSTALL.md](INSTALL.md) 跑通 GEM 的五个入口。后处理另需 [GMR](https://github.com/YanjieZe/GMR) 源码、[GR00T-WholeBodyControl](https://github.com/NVlabs/GR00T-WholeBodyControl) 的 G1 XML/网格，以及从 [SMPL-X 官方](https://smpl-x.is.tue.mpg.de/) 获许可取得的 `SMPLX_NEUTRAL.pkl`。它与 GEM 使用的 `.npz` 是不同文件，不能互换。建议从交付根目录执行：

```bash
mkdir -p external
git clone https://github.com/YanjieZe/GMR.git external/GMR
git -C external/GMR checkout bb1bbe40774794fceb2a7c579a3464a28e68c844
git -C external/GMR apply "$PWD/GEM/provenance/GMR_required.patch"
git clone https://github.com/NVlabs/GR00T-WholeBodyControl.git external/GR00T-WholeBodyControl
git -C external/GR00T-WholeBodyControl checkout 3d3e593369bc1384a8f5d1f22830bf20cb3a6047
```

把获许可的 `SMPLX_NEUTRAL.pkl` 放在 `external/GMR/assets/body_models/smplx/`。本次参考文件大小为 544,173,380 B，SHA256 为 `381c808965deb4f5e845f8c3eddb0cd69930cc72e5774ce4f34c4ce3cf058361`。G1 XML 应位于 `external/GR00T-WholeBodyControl/gear_sonic_deploy/g1/g1_29dof.xml`，参考 SHA256 为 `439c1ec0806583d73b492da9484b0cb9e9eae215e0d9506e3c2fa69016733532`；它引用的网格文件也须一同保留。GMR 使用其仓库内的 `assets/unitree_g1/` 机器人资产。

## 2. 建立 GMR 环境

GEM 与 GMR 使用不同的依赖组合，分别安装。GMR 环境示例：

```bash
bash install_gmr_env.sh
GMR_PYTHON_BIN="$PWD/.venv-gmr/bin/python" bash run_postprocess.sh --help
```

脚本先安装 PyTorch 2.6.0 CUDA 12.4，再安装 [GMR 依赖版本](requirements-gmr.txt)，最后以 editable 模式安装 `external/GMR`。需要能访问 Python 包索引；无外网时可像 `INSTALL.md` 一样使用本地 wheel 仓库。已有兼容环境可设置 `GMR_PYTHON_BIN=/absolute/path/to/python` 跳过安装。若外部仓库放在其他位置，设置 `GMR_ROOT` 和 `SONIC_XML` 为对应绝对路径。全新机器从零安装尚未完成独立验收，应在目标机器自行检查安装与下面的最小转换。

## 3. 运行完整流程

先运行五入口全量样例，再运行文本预测生成段封装，最后执行后处理：

```bash
bash run_full.sh
bash five_demo/run/run_text_pred_batch.sh
bash run_postprocess.sh
```

默认 `--profile run` 从 `five_demo/outputs/` 精确选择 75 条：混合 5、文本生成/补全 15、文本预测生成段 15、视频 HPE 5、六类视频预测 30、交替混合 5。文本预测从 `text_pred/generated/` 读取，避免将条件描述段误当作预测结果；视频预测当前保留观测视频段与生成段的整条序列，段范围可在原 `smpl_params.pt` 的 `segment_info` 中核对。

后处理写入初始为空的 `five_demo/postprocess_outputs/`，每条任务包含：

```text
gmr/<任务路径>/smplx_motion.npz
gmr/<任务路径>/robot_motion.pkl
sonic/<任务路径>/{joint_pos,joint_vel,body_pos,body_quat,body_lin_vel,body_ang_vel}.csv
sonic/<任务路径>/{metadata,info}.txt
run_logs/<任务路径>.log
input_manifest.tsv
run_config.json
status.tsv
```

`smplx_motion.npz` 含 30 Hz 的人体轴角、根平移与形状参数；`robot_motion.pkl` 含 30 Hz 的 G1 根位置（米）、根四元数（`xyzw`）和 29 个 MuJoCo 顺序关节；SONIC CSV 是 50 Hz、29 个 IsaacLab 顺序关节及 14 个身体的轨迹，身体四元数为 `wxyz`。`input_manifest.tsv` 记录输入哈希，`run_config.json` 记录代码、模型和 XML 哈希，`status.tsv` 定位失败样例，对应日志在 `run_logs/`。所有样例完成后应显示 `postprocess verification: 75/75`。更换输入、代码、资源或参数时，使用新的 `--output-root`，避免复用旧结果。

## 4. 从随包参考 SMPL 复算

不用重跑 GEM 推理，也可从参考结果验证 GMR/SONIC 环境。下面的 `reference` 档选择 75 条正式任务；`all` 档处理随包全部 95 个 SMPL 文件，包括额外的 TXT_GEN 单组副本与 15 个预测原始完整序列：

```bash
bash run_postprocess.sh --profile reference \
  --input-root "$PWD/five_demo/reference_outputs" \
  --output-root "$PWD/five_demo/postprocess_from_reference"

bash run_postprocess.sh --profile all \
  --input-root "$PWD/five_demo/reference_outputs" \
  --output-root "$PWD/five_demo/postprocess_all_reference"
```

已经取得后处理文件时，可以只核对随包的 95 条参考结果：

```bash
bash run_postprocess.sh --profile all --verify-only \
  --input-root "$PWD/five_demo/reference_outputs" \
  --output-root "$PWD/five_demo/reference_postprocess"
```

`--verify-only` 检查每条 SMPL-X/G1/SONIC 的文件齐全、张量维度、帧数与有限值；它不评价动作是否符合文字含义，也不检验机器人动力学可行性。参考运行记录见 [REPRO_REPORT.md](REPRO_REPORT.md)。

随包参考结果另有 `reference_postprocess/input_manifest.tsv`、`result_manifest.tsv`、`run_config.json`、`status.tsv` 和 `SHA256SUMS`，用于逐条核对来源与各阶段文件哈希。
