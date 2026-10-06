# RoboSteer 模型资源——公开参考版

[English](README.md) · [公开范围](PUBLIC_RELEASE_SCOPE.md) · [MIT 许可范围](LICENSE_SCOPE.md) · [模型状态表](model_index.csv)

本仓库提供九条动作与机器人流水线的本项目教程和参考脚本。**九个模型目录目前均仅供参考，不构成仅凭公开文件即可运行的完整复现包。** 上游项目源码、模型权重、人体模型和机器人资产须由使用者按各自许可另行取得。历史验证记录说明原有环境中做过的检查，不等于当前公开包已经在全新机器上复现。

| 模型 | 当前公开内容 | 主要外部依赖 |
| --- | --- | --- |
| [MotionCraft](models/motioncraft/README_zh.md) | 原创流水线参考脚本和教程 | 上游 MotionCraft、GMR、SONIC 源码与资源 |
| [GEM](models/gem/README_zh.md) | 五类任务编排脚本、教程、自建样例及参考后处理结果 | 上游 GEM、GMR、SONIC 源码与资源 |
| [Language of Motion](models/language_of_motion/README.md) | 参考工具和教程 | 上游 LoM、GMR、SONIC 源码与资源 |
| [ListenDenoiseAction](models/listen_denoise_action/README_zh.md) | 原创适配与编排脚本 | 上游 LDA、GMR 源码与资源 |
| [TextOp](models/textop/README.md) | 参考教程、原创检查脚本和文本样例 | 上游 TextOp 源码与资源 |
| [UH-1](models/uh1/README.md) | 教程和文本样例 | 上游 UH-1 源码与资源 |
| [UniAct](models/uniact/README_ZH.md) | 参考工具和教程 | 上游 UniAct、GMR、SONIC 源码与资源 |
| [video2robot](models/video2robot/README.md) | 参考脚本和教程 | 上游 video2robot、PromptHMR、GMR 与资源 |
| [BFM-Zero](models/bfm_zero/README.md) | 参考教程和来源记录 | 未公开的项目适配脚本及上游资源 |

这些文件用于理解流程，并在自行取得依赖后开展适配。旧版详细教程中的命令记录历史运行，部分路径指向本公开版特意排除的文件。使用前先阅读相应模型目录的 `PUBLIC_SCOPE.md`。

本仓库是文件资源集合，不提供 `load_dataset()` 表格接口。项目原创脚本与原创说明按[指定范围](LICENSE_SCOPE.md)适用 [MIT 许可证](LICENSE)；上游项目、权重、输入和生成结果不适用该授权。见[第三方说明](THIRD_PARTY_NOTICES.md)及各模型来源链接。[安装约定](docs/installation.md)说明当前参考版的边界。压缩包用相邻的 `.sha256` 核对；目录内 `SHA256SUMS` 仅覆盖其中列出的解包文件。
