> **历史教程 / Historical guide：** 下文凡称“本包包含源码、入口、参考结果”均指旧版完整工作环境，不适用于当前公开参考版。当前版仅供阅读，命令不能仅凭本目录运行。 Claims below that source, entrypoints or results are bundled describe the previous full environment, not this public reference edition. See [PUBLIC_SCOPE.md](PUBLIC_SCOPE.md).

# ListenDenoiseAction 公开交付信息

版本：`0.1.0-rc1`。本文面向公开发布审核，描述本目录提供的适配层、运行入口、资源边界和验证范围。目录不包含 LDA 上游完整源码、模型权重、音频数据、SMPL-X 模型文件或 G1/SONIC 机器人资产。

## 1. 模型与官方来源

- Listen, Denoise, Action! Audio-Driven Motion Synthesis with Diffusion Models（ACM TOG 42(4), 2023）。论文：[arXiv:2211.09707](https://arxiv.org/abs/2211.09707)，DOI：[10.1145/3592458](https://doi.org/10.1145/3592458)。
- LDA 官方仓库：[simonalexanderson/ListenDenoiseAction](https://github.com/simonalexanderson/ListenDenoiseAction)，固定 commit：`9b0885b699913b55283c24ad624bd4e8e8ed957c`。
- GMR 官方仓库：[YanjieZe/GMR](https://github.com/YanjieZe/GMR)，固定 commit：`bb1bbe40774794fceb2a7c579a3464a28e68c844`。
- SONIC/G1 资产来源：[NVlabs/GR00T-WholeBodyControl](https://github.com/NVlabs/GR00T-WholeBodyControl)。

## 2. 本目录解决的问题

RoboSteer 适配链为：音频 → LDA 人体动作（BVH）→ GMR/SMPL-X 重定向 → G1 PKL → SONIC CSV。交付内容是四个适配脚本、必要的 LDA 推理补丁、两个 GMR 路径清理脚本、三条阶段入口和资源/验证说明。

## 3. 固定版本与运行方式

运行前从官方来源取得 LDA、GMR 和所需外部资源，再执行 `scripts/apply_adapters.py`。该脚本检查固定 commit 和干净工作树，复制适配文件，不会重置或删除用户文件。

三条入口分别是：

1. `scripts/run_audio_to_bvh.sh`
2. `scripts/run_bvh_to_robot.sh`
3. `scripts/run_robot_to_sonic.sh`

示例命令和参数见 [README_zh.md](README_zh.md)。中间目录必须使用空目录；各阶段会保留特征、BVH、SMPL-X、G1 PKL 和 SONIC 文件，便于逐阶段检查。

## 4. 环境要求

本交付以已经可运行的 `lda` 和 `gmr` 环境为验证基线，不要求用户新建 Conda 环境。`environment/` 中的 yml、requirements 和 constraints 文件只作为迁移参考；验证报告没有把全新环境安装宣称为已通过。

## 5. 外部资源与许可边界

全部外部资源均为 `included=false`，包括 LDA 权重和元数据、SMPL-X、GMR/G1 XML 与 mesh、SONIC XML 与 mesh、输入音频和参考特征。资源用途、官方链接、固定版本和本地核验哈希见 [resources/resources.yaml](resources/resources.yaml) 与 [resources/RESOURCE_SCOPE_zh.md](resources/RESOURCE_SCOPE_zh.md)。下载和再分发前必须分别遵守上游许可。

LDA 上游和权重的研究用途及再分发限制不能由本适配包改变。SMPL-X 使用官方模型条款；GMR 代码为 MIT；GMR G1 资产保留 BSD-3-Clause 声明；SONIC 资产的具体再分发范围需要按其来源确认。

## 6. 验证状态

在既有环境中完成 10/10 条样例的全流程运行和结构检查；一条样例通过了三条公开入口的隔离冒烟测试。验证覆盖文件生成、帧数、维度、有限值、四元数归一化和 SONIC 50 FPS 输出，不覆盖物理跟踪、全新环境安装或跨设备逐字节确定性。详见 [validation/report.md](validation/report.md)。

## 7. 公开发布前仍需确认

适配脚本作者已确认这些脚本由其编写并允许公开发布。原创适配层和编排代码采用 MIT License，版权主体为 `cxt`，许可证文本见包根目录 `LICENSE`；该许可不覆盖 LDA、权重、SMPL-X 或机器人资产。

## 8. 相关引用

- LDA：Alexanderson, Nagy, Beskow, Henter. “Listen, Denoise, Action! Audio-Driven Motion Synthesis with Diffusion Models.” ACM TOG 42(4), 2023。
- TISA 音频特征：[ulmewennberg/tisa](https://github.com/ulmewennberg/tisa)，论文：[ACL 2021](https://aclanthology.org/2021.acl-short.18)。
- GMR：[YanjieZe/GMR](https://github.com/YanjieZe/GMR)。
- GMR 论文：Araújo, Ze, Xu, Wu, Liu. “Retargeting Matters: General Motion Retargeting for Humanoid Motion Tracking.” [arXiv:2510.02252](https://arxiv.org/abs/2510.02252)。
- SMPL-X：[官方项目页](https://smpl-x.is.tue.mpg.de/)及[模型许可](https://smpl-x.is.tue.mpg.de/modellicense.html)。
- SONIC/G1：[NVlabs/GR00T-WholeBodyControl](https://github.com/NVlabs/GR00T-WholeBodyControl)。
