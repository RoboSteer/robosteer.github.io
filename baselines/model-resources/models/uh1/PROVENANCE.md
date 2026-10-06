> **历史教程 / Historical guide：** 下文凡称“本包包含源码、入口、参考结果”均指旧版完整工作环境，不适用于当前公开参考版。当前版仅供阅读，命令不能仅凭本目录运行。 Claims below that source, entrypoints or results are bundled describe the previous full environment, not this public reference edition. See [PUBLIC_SCOPE.md](PUBLIC_SCOPE.md).

# 来源与公开边界

- UH-1 原项目：[sihengz02/UH-1](https://github.com/sihengz02/UH-1)，本地基线 commit `d9add1b336bf0366fe6dc44564c94fb771dec3ab`。本机源码包含后续未提交的推理和转换脚本改动；准确文件哈希见内部 `source_manifest.json`。
- 批量文本推理、预测占位片段导出、运行记录和 H1→G1 SONIC 转换是本地适配流程；不是 UH-1 原作者对预测任务或真实机器人控制的能力声明。
- 转换依赖 [GMR](https://github.com/YanjieZe/GMR) 和 [GR00T-WholeBodyControl](https://github.com/NVlabs/GR00T-WholeBodyControl) 的 G1 资源。分别遵守其仓库许可证和资产声明。
- UH-1 仓库根目录未发现覆盖该项目的许可证。`legged_gym/`、`rsl_rl/` 各自的许可证不能自动覆盖 UH-1 根目录、模型、脚本或权重。因此完整源码快照和权重留在内部，不直接作为公开包再分发。要发布可运行源码，先取得或确认 UH-1 代码和相关资产的再分发许可。
- `public/examples/` 是用户允许公开的少量验证输入，仍应在正式对外发布前核对其上游数据授权和个人信息。公开资料不含原始大数据目录、服务器私有配置、权重、运行日志或历史输出。
