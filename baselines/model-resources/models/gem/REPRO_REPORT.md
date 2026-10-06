> **历史教程 / Historical guide：** 下文凡称“本包包含源码、入口、参考结果”均指旧版完整工作环境，不适用于当前公开参考版。当前版仅供阅读，命令不能仅凭本目录运行。 Claims below that source, entrypoints or results are bundled describe the previous full environment, not this public reference edition. See [PUBLIC_SCOPE.md](PUBLIC_SCOPE.md).

# 交付包参考验收记录

## 已实测的范围

参考验收使用 Linux、Python 3.10、PyTorch 2.6.0+cu124 和 NVIDIA GPU。GEM 模块从本包 `GEM/` 加载，五个入口与配置从本包 `five_demo/mini_repo/` 加载；模型资源由测试环境单独提供，不在交付压缩包中。以下数字供读者核对预期目录和文件数量，不能代替本机验收。

执行 `preflight.sh --verify-hashes` 时，GEM、SMPL-X、T5 编码器、HMR2、ViTPose、YOLO 六份资源均与 [资源清单](RESOURCES.md) 的 SHA256 一致。`five_demo/SOURCE_MANIFEST.tsv` 记录 155 个脚本、配置和输入的来源与交付副本哈希；三个入口仅修改了示例或默认数据路径，其余副本与来源一致。`GEM/SHA256SUMS` 对源码快照核验通过。

在初始为空的 `five_demo/outputs/` 中运行 `run_smoke.sh`，参考验收数量如下：

| 入口 | 预期 | 新生成且通过张量检查 |
| --- | ---: | ---: |
| 单次混合 | 1 | 1 |
| 文本批量 TXT_GEN | 5 | 5 |
| 视频 HPE | 5 | 5 |
| 视频预测 FORE/HUMAN | 5 | 5 |
| 交替混合 | 5 | 5 |
| 合计 | 21 | 21 |

`verify_outputs.py` 检查每个文件的 SMPL 参数形状、有限值、片段边界、预测失败清单及交替任务状态；参考记录的输出为 `smoke verification: PASS`。各类别结果另见 [five_demo/RUN_VALIDATION.md](five_demo/RUN_VALIDATION.md)。

## 全量样例

随后运行 `run_full.sh`，按全量目标检查结果：混合 5/5、六组文本 30/30、HPE 5/5、六类视频预测 30/30、交替混合 5/5，共 **75/75**；参考记录的输出为 `full verification: PASS`。预测失败清单为空。已有结果由 `--resume` 跳过；由于先运行了最小验收，目录还额外保留单类文本 5 个和单类预测 5 个结果，因此 `find outputs -name smpl_params.pt` 的总数是 85。最小与全量的验收计数日志分别保存在 `validation/verify_smoke.log`、`validation/verify_full.log`。

## 文本预测生成段

文本预测专用封装使用原文本批量入口推理，再筛选目标生成段。FORE、INTER、RETRO 各一条的端到端运行得到 3/3 个完整结果和 3/3 个生成段结果；随包三组各 5 条的参考结果经筛选和张量检查为 **15/15**。计数记录在 `validation/verify_text_pred.log`，使用方法见 [文本预测教程](five_demo/guides/text_prediction.md)。

## GMR 与 SONIC 后处理

从本包 `five_demo/reference_outputs/` 的全部 95 个 SMPL 文件继续执行转换：SMPL-X `.npz` **95/95**、GMR G1 `.pkl` **95/95**、SONIC 文件夹 **95/95**。逐条检查了 SMPL-X 与 G1 的帧数、形状和有限值，以及 SONIC 六个 CSV 的帧数、列数、有限值与元数据；结果为 **95/95**，记录在 `validation/verify_postprocess.log`。产物在 `five_demo/reference_postprocess/`，配置与重新运行命令见 [POSTPROCESS.md](POSTPROCESS.md)。

这 95 份参考结果包含额外的单组文本副本和 15 份预测原始完整序列。正式处理五入口全量任务时，`run_postprocess.sh` 选择 75 份互不重复的结果，并使用 15 份文本预测的生成段代替其原始完整序列。视频预测后处理目前保留观测段与生成段的完整序列。

另外用 `run_postprocess.sh --profile reference` 独立复算 75 条，数值校验 **75/75**。与随包后处理参考文件比较，750 个阶段文件中 743 个逐字节相同；`TXT_INTER_02` 的 G1 PKL 与其 6 个 SONIC CSV 存在小幅数值差异，G1 关节最大绝对差约 **0.00507 rad**，文件形状与有限值检查仍通过。记录见 `validation/verify_postprocess_repeat.log`；因此不以逐字节一致作为复现验收条件。

## 尚未验证与已知限制

- `install_env.sh` 给出从空 Python 3.10 环境重建的顺序和配套版本；**全新机器从零安装未纳入这份参考验收**。读者仍需自行完成安装、预检和最小验收。
- 上游 `GEM/setup.cfg` 钉住了不同于本包依赖清单的旧 NumPy、timm 和 Ultralytics 版本；交付安装脚本先安装清单版本，再用 `--no-deps` 安装源码。若目标机器的 Python、驱动或平台不兼容，需按预检错误调整。
- 五条 `--no_render` 示例使用 OpenCV 读取视频；其他渲染或导出用途应安装系统级 `ffmpeg`/`ffprobe`。
- GEM 模型初始化即读取获许可的 `SMPLX_NEUTRAL.npz`，关闭渲染也需要它；缺失时会在 `gem/utils/body_model/smplx_lite.py` 报错。
- 检查通过表示流程和显式数值条件通过；不表示与参考结果逐位一致，也不评价动作语义、真实视频质量或机器人安全。单次混合和文本批量入口未固定随机种子，不能据此要求逐位复现。
- GMR/SONIC 的参考转换使用已有兼容环境及获许可的外部资源；`install_gmr_env.sh` 的全新机器从零安装尚未独立验证。GMR/SONIC 结果是研究文件格式转换记录，未进行机器人实机安全验收。
